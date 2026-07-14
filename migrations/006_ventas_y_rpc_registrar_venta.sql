-- ============================================================
-- Big Royal SaaS — Migración 006: Ventas + auto-descuento de stock
-- (CU-06: Registrar Venta) — RF-INV-40, RN01, RNF-REL-01
-- ============================================================
-- Crea las tablas 'ventas' y 'detalle_ventas' (no existían en la base)
-- y la RPC transaccional registrar_venta(), que descuenta el stock de
-- los insumos según la receta del producto.
--
-- Depende de: 004 (restaurante_actual() / rol_actual()).
-- Es idempotente: CREATE TABLE IF NOT EXISTS + CREATE OR REPLACE.
-- ============================================================


-- ============================================================
-- 1. Tablas
--    detalle_ventas NO lleva restaurante_id: el tenant se deriva de
--    la venta padre, igual que 'recetas' y 'detalle_pedidos'.
--    precio_unitario guarda una FOTO del precio al momento de vender;
--    si mañana cambia productos.precio, el historial no se falsea.
-- ============================================================
CREATE TABLE IF NOT EXISTS ventas (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    usuario_id     UUID NOT NULL REFERENCES usuarios(id),
    total          NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venta_id        UUID NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id     UUID NOT NULL REFERENCES productos(id),
    cantidad        NUMERIC NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ventas_restaurante_fecha_idx
    ON ventas (restaurante_id, created_at DESC);

CREATE INDEX IF NOT EXISTS detalle_ventas_venta_idx
    ON detalle_ventas (venta_id);


-- ============================================================
-- 2. Políticas RLS
--    Solo se definen políticas de SELECT (por tenant). NO hay política
--    de INSERT a propósito: así ninguna venta puede escribirse por la
--    vía directa saltándose el auto-descuento de stock. La única puerta
--    de entrada es registrar_venta(), que al ser SECURITY DEFINER no
--    pasa por RLS. Esto convierte la RN01 ("todo producto vendido debe
--    descontar stock") en una garantía de la base de datos, no en una
--    convención que la app deba recordar.
--
--    El SELECT no filtra por rol: el Cajero necesita ver la venta que
--    acaba de registrar y el Administrador necesita el historial
--    completo para los reportes del CU-07.
-- ============================================================
ALTER TABLE ventas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ventas_select_tenant ON ventas;
CREATE POLICY ventas_select_tenant ON ventas
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

ALTER TABLE detalle_ventas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS detalle_ventas_select_tenant ON detalle_ventas;
CREATE POLICY detalle_ventas_select_tenant ON detalle_ventas
    FOR SELECT USING (
        venta_id IN (
            SELECT id FROM ventas
            WHERE restaurante_id = public.restaurante_actual()
        )
    );


-- ============================================================
-- 3. RPC registrar_venta — auto-descuento atómico (RF-INV-40)
-- ============================================================
-- POR QUÉ ES SECURITY DEFINER (y registrar_ajuste_inventario NO lo es):
--
--   La RN02 reserva los ajustes manuales de stock al Administrador, y
--   las políticas de 'insumos' aplican esa regla: solo el Admin puede
--   hacer UPDATE. Pero el CU-06 exige que sea el CAJERO quien dispare
--   el descuento al vender. Darle al Cajero permiso de UPDATE sobre
--   'insumos' rompería la RN02 (podría editar el stock a mano desde
--   cualquier cliente). La salida correcta es esta función: corre con
--   los permisos del dueño, descuenta stock por la vía controlada, y
--   el Cajero nunca gana permiso de escritura directa.
--
--   El precio de SECURITY DEFINER es que aquí NO hay RLS que nos
--   proteja: las comprobaciones de tenant de abajo son la ÚNICA
--   barrera entre restaurantes. No las quites ni las relajes.
--
-- PRODUCTO SIN RECETA (CU-06, flujo alterno 2.1: "el sistema alerta al
--   Cajero antes de continuar"): la función rechaza la venta con
--   PRODUCTO_SIN_RECETA. La app muestra la alerta y, si el Cajero
--   confirma, vuelve a llamar con p_confirmar_sin_receta => true.
--
-- ATOMICIDAD (flujo alterno 4.1 / RNF-REL-01): todo el cuerpo corre en
--   una sola transacción. Cualquier RAISE revierte la venta, el detalle
--   y los descuentos ya aplicados. No puede quedar media venta.
-- ============================================================
CREATE OR REPLACE FUNCTION public.registrar_venta(
    p_producto_id          UUID,
    p_cantidad             NUMERIC,
    p_confirmar_sin_receta BOOLEAN DEFAULT FALSE
)
RETURNS UUID                     -- id de la venta registrada
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_usuario_id     UUID := auth.uid();
    v_restaurante_id UUID;
    v_rol            TEXT;
    v_precio         NUMERIC;
    v_venta_id       UUID;
    v_lineas_receta  INT;
    v_requerido      NUMERIC;
    v_stock          NUMERIC;
    r                RECORD;
BEGIN
    IF v_usuario_id IS NULL THEN
        RAISE EXCEPTION 'NO_AUTENTICADO';
    END IF;

    IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
        RAISE EXCEPTION 'CANTIDAD_INVALIDA';
    END IF;

    -- Membresía del llamante: única barrera de tenant (ver nota arriba).
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

    -- RN03: el producto debe ser del restaurante del llamante.
    SELECT precio
      INTO v_precio
      FROM productos
     WHERE id = p_producto_id
       AND restaurante_id = v_restaurante_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRODUCTO_NO_ENCONTRADO';
    END IF;

    SELECT count(*)
      INTO v_lineas_receta
      FROM recetas
     WHERE producto_id = p_producto_id;

    IF v_lineas_receta = 0 AND NOT p_confirmar_sin_receta THEN
        RAISE EXCEPTION 'PRODUCTO_SIN_RECETA';
    END IF;

    INSERT INTO ventas (restaurante_id, usuario_id, total)
    VALUES (v_restaurante_id, v_usuario_id, coalesce(v_precio, 0) * p_cantidad)
    RETURNING id INTO v_venta_id;

    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario)
    VALUES (v_venta_id, p_producto_id, p_cantidad, coalesce(v_precio, 0));

    -- RN01: auto-descuento por receta.
    -- El ORDER BY insumo_id no es cosmético: fija un orden de bloqueo
    -- estable para que dos ventas simultáneas que comparten insumos no
    -- se bloqueen en abrazo mortal (deadlock).
    FOR r IN
        SELECT insumo_id, cantidad_consumo
          FROM recetas
         WHERE producto_id = p_producto_id
         ORDER BY insumo_id
    LOOP
        v_requerido := r.cantidad_consumo * p_cantidad;

        SELECT stock_actual
          INTO v_stock
          FROM insumos
         WHERE id = r.insumo_id
           AND restaurante_id = v_restaurante_id
         FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'INSUMO_NO_ENCONTRADO';
        END IF;

        IF v_stock - v_requerido < 0 THEN
            RAISE EXCEPTION 'STOCK_INSUFICIENTE';
        END IF;

        UPDATE insumos
           SET stock_actual = v_stock - v_requerido
         WHERE id = r.insumo_id;

        -- Auditoría: cantidad negativa porque la venta resta stock,
        -- misma convención de signo que registrar_ajuste_inventario.
        INSERT INTO auditoria_inventario (
            restaurante_id, insumo_id, usuario_id,
            tipo_operacion, cantidad_afectada, motivo
        ) VALUES (
            v_restaurante_id, r.insumo_id, v_usuario_id,
            'Venta', -v_requerido, 'Venta ' || v_venta_id::text
        );
    END LOOP;

    RETURN v_venta_id;
END;
$$;

-- Nadie debe poder ejecutarla salvo usuarios autenticados: al ser
-- SECURITY DEFINER, un GRANT a 'anon' la convertiría en una puerta
-- abierta para escribir en insumos sin sesión.
REVOKE ALL ON FUNCTION public.registrar_venta(UUID, NUMERIC, BOOLEAN) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.registrar_venta(UUID, NUMERIC, BOOLEAN) FROM anon;
GRANT EXECUTE ON FUNCTION public.registrar_venta(UUID, NUMERIC, BOOLEAN) TO authenticated;
