-- ============================================================
-- Big Royal SaaS — Migración 010: la venta EXIGE receta (CU-15)
-- ============================================================
-- Cambio de regla de negocio: un producto sin receta ya NO se puede vender.
-- Antes (migración 008) la RPC aceptaba un parámetro p_confirmar_sin_receta
-- que permitía registrar la venta de un producto sin receta sin descontar
-- stock (flujo alterno 2.1 "continuar de todos modos"). Se elimina esa vía:
-- ahora, si cualquier ítem del pedido no tiene receta, la venta se rechaza
-- por completo con PRODUCTO_SIN_RECETA.
--
-- Así toda venta controla stock: no hay forma de vender algo que no descuente
-- inventario. Es una garantía de la base, no una convención del app.
--
-- Se cambia la firma: de (jsonb, boolean) a (jsonb). Por eso se DROPEA la
-- versión anterior antes de recrearla. El único llamador es la app, que se
-- actualiza en el mismo cambio.
--
-- Depende de: 004 (usuarios/rol), 006 (tablas ventas y detalle_ventas).
-- ============================================================

DROP FUNCTION IF EXISTS public.registrar_venta_multiple(jsonb, boolean);

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

    -- Nueva regla: la venta EXIGE que todos los productos tengan receta.
    -- Sin escape: si alguno no la tiene, se rechaza el pedido completo.
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

    -- RN01: auto-descuento por receta, consolidando el consumo por insumo.
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
            v_stock NUMERIC;
        BEGIN
            SELECT stock_actual
              INTO v_stock
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

            UPDATE insumos
               SET stock_actual = v_stock - v_consumo.requerido
             WHERE id = v_consumo.insumo_id;

            INSERT INTO auditoria_inventario (
                restaurante_id, insumo_id, usuario_id,
                tipo_operacion, cantidad_afectada, motivo
            ) VALUES (
                v_restaurante_id, v_consumo.insumo_id, v_usuario_id,
                'Venta', -v_consumo.requerido, 'Venta ' || v_venta_id::text
            );
        END;
    END LOOP;

    RETURN v_venta_id;
END;
$$;

REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB) FROM anon;
GRANT EXECUTE ON FUNCTION public.registrar_venta_multiple(JSONB) TO authenticated;
