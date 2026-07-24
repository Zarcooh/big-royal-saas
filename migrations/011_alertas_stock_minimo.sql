-- ============================================================
-- Big Royal SaaS — Migración 011: Alertas de stock mínimo (CU-17 / RF-INV-18)
-- ============================================================
-- Genera una alerta automática cuando, tras el auto-descuento de una venta,
-- el stock de un insumo CRUZA a su nivel mínimo (pasa de estar por encima a
-- estar en o por debajo del mínimo). Se registra en la tabla 'alertas_stock'
-- para que el Administrador la vea y la marque como atendida.
--
-- Solo se genera en el "cruce" (no en cada venta mientras siga crítico) para
-- no duplicar alertas del mismo insumo una y otra vez.
--
-- Depende de: 004 (restaurante_actual/rol_actual), 006 (insumos/auditoria),
-- 010 (registrar_venta_multiple). Idempotente.
-- ============================================================

-- 1. Tabla de alertas
CREATE TABLE IF NOT EXISTS alertas_stock (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    insumo_id      UUID NOT NULL REFERENCES insumos(id) ON DELETE CASCADE,
    stock_actual   NUMERIC(10, 2) NOT NULL,
    stock_minimo   NUMERIC(10, 2) NOT NULL,
    origen         VARCHAR(30) NOT NULL DEFAULT 'Venta',
    atendida       BOOLEAN NOT NULL DEFAULT false,
    creada_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS alertas_stock_rest_idx
    ON alertas_stock (restaurante_id, atendida, creada_en DESC);

-- 2. RLS: lectura por tenant; marcar atendida solo el Admin del tenant.
--    NO hay política de INSERT a propósito: solo la escribe la RPC
--    registrar_venta_multiple (SECURITY DEFINER, no pasa por RLS), igual que
--    'ventas'. Así la alerta siempre nace del auto-descuento y no a mano.
ALTER TABLE alertas_stock ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS alertas_select_tenant ON alertas_stock;
CREATE POLICY alertas_select_tenant ON alertas_stock
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS alertas_update_admin ON alertas_stock;
CREATE POLICY alertas_update_admin ON alertas_stock
    FOR UPDATE
    USING (restaurante_id = public.restaurante_actual()
           AND public.rol_actual() = 'Administrador')
    WITH CHECK (restaurante_id = public.restaurante_actual());


-- 3. RPC registrar_venta_multiple: se le agrega la generación de alertas.
--    (Mismo cuerpo de la migración 010 + el bloque de alerta en el loop.)
CREATE OR REPLACE FUNCTION public.registrar_venta_multiple(
    p_items JSONB
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_usuario_id     UUID := auth.uid();
    v_restaurante_id UUID;
    v_rol            TEXT;
    v_venta_id       UUID;
    v_total          NUMERIC;
    v_items          INT;
    v_invalidos      INT;
    v_ajenos         INT;
    v_sin_receta     INT;
    v_consumo        RECORD;
BEGIN
    IF v_usuario_id IS NULL THEN
        RAISE EXCEPTION 'NO_AUTENTICADO';
    END IF;

    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array'
       OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'CARRITO_VACIO';
    END IF;

    SELECT restaurante_id, rol
      INTO v_restaurante_id, v_rol
      FROM usuarios
     WHERE id = v_usuario_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'USUARIO_SIN_PERFIL';
    END IF;

    IF v_rol NOT IN ('Cajero', 'Administrador') THEN
        RAISE EXCEPTION 'ROL_NO_AUTORIZADO';
    END IF;

    WITH items AS (
        SELECT it.producto_id, sum(it.cantidad) AS cantidad
          FROM jsonb_to_recordset(p_items)
            AS it(producto_id UUID, cantidad NUMERIC)
         GROUP BY it.producto_id
    )
    SELECT count(*),
           count(*) FILTER (
               WHERE i.producto_id IS NULL OR i.cantidad IS NULL OR i.cantidad <= 0
           ),
           count(*) FILTER (
               WHERE NOT EXISTS (
                   SELECT 1 FROM productos p
                    WHERE p.id = i.producto_id
                      AND p.restaurante_id = v_restaurante_id)
           ),
           count(*) FILTER (
               WHERE NOT EXISTS (
                   SELECT 1 FROM recetas rec WHERE rec.producto_id = i.producto_id)
           )
      INTO v_items, v_invalidos, v_ajenos, v_sin_receta
      FROM items i;

    IF v_items = 0 THEN
        RAISE EXCEPTION 'CARRITO_VACIO';
    END IF;

    IF v_invalidos > 0 THEN
        RAISE EXCEPTION 'CANTIDAD_INVALIDA';
    END IF;

    IF v_ajenos > 0 THEN
        RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO';
    END IF;

    IF v_sin_receta > 0 THEN
        RAISE EXCEPTION 'PRODUCTO_SIN_RECETA';
    END IF;

    WITH items AS (
        SELECT it.producto_id, sum(it.cantidad) AS cantidad
          FROM jsonb_to_recordset(p_items)
            AS it(producto_id UUID, cantidad NUMERIC)
         GROUP BY it.producto_id
    )
    SELECT coalesce(sum(coalesce(p.precio, 0) * i.cantidad), 0)
      INTO v_total
      FROM items i
      JOIN productos p ON p.id = i.producto_id;

    INSERT INTO ventas (restaurante_id, usuario_id, total)
    VALUES (v_restaurante_id, v_usuario_id, v_total)
    RETURNING id INTO v_venta_id;

    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario)
    SELECT v_venta_id, i.producto_id, i.cantidad, coalesce(p.precio, 0)
      FROM (
          SELECT it.producto_id, sum(it.cantidad) AS cantidad
            FROM jsonb_to_recordset(p_items)
              AS it(producto_id UUID, cantidad NUMERIC)
           GROUP BY it.producto_id
      ) i
      JOIN productos p ON p.id = i.producto_id;

    FOR v_consumo IN
        SELECT rec.insumo_id,
               sum(rec.cantidad_consumo * i.cantidad) AS requerido
          FROM (
              SELECT it.producto_id, sum(it.cantidad) AS cantidad
                FROM jsonb_to_recordset(p_items)
                  AS it(producto_id UUID, cantidad NUMERIC)
               GROUP BY it.producto_id
          ) i
          JOIN recetas rec ON rec.producto_id = i.producto_id
         GROUP BY rec.insumo_id
         ORDER BY rec.insumo_id
    LOOP
        DECLARE
            v_stock  NUMERIC;
            v_minimo NUMERIC;
            v_nuevo  NUMERIC;
        BEGIN
            SELECT stock_actual, stock_minimo
              INTO v_stock, v_minimo
              FROM insumos
             WHERE id = v_consumo.insumo_id
               AND restaurante_id = v_restaurante_id
             FOR UPDATE;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'INSUMO_NO_ENCONTRADO';
            END IF;

            IF v_stock - v_consumo.requerido < 0 THEN
                RAISE EXCEPTION 'STOCK_INSUFICIENTE';
            END IF;

            v_nuevo := v_stock - v_consumo.requerido;

            UPDATE insumos
               SET stock_actual = v_nuevo
             WHERE id = v_consumo.insumo_id;

            INSERT INTO auditoria_inventario (
                restaurante_id, insumo_id, usuario_id,
                tipo_operacion, cantidad_afectada, motivo
            ) VALUES (
                v_restaurante_id, v_consumo.insumo_id, v_usuario_id,
                'Venta', -v_consumo.requerido, 'Venta ' || v_venta_id::text
            );

            -- RF-INV-18: alerta automática si el insumo CRUZA a su mínimo
            -- (estaba por encima y ahora queda en o por debajo).
            IF v_minimo IS NOT NULL
               AND v_stock > v_minimo
               AND v_nuevo <= v_minimo THEN
                INSERT INTO alertas_stock (
                    restaurante_id, insumo_id, stock_actual, stock_minimo, origen
                ) VALUES (
                    v_restaurante_id, v_consumo.insumo_id, v_nuevo, v_minimo, 'Venta'
                );
            END IF;
        END;
    END LOOP;

    RETURN v_venta_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB) FROM anon;
GRANT EXECUTE ON FUNCTION public.registrar_venta_multiple(JSONB) TO authenticated;
