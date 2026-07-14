-- ============================================================
-- Big Royal SaaS — Migración 005: Políticas RLS de abastecimiento
-- (proveedores, pedidos, detalle_pedidos) — habilita CU-05
-- ============================================================
-- CONTEXTO: las tres tablas ya existían en la base desplegada con
-- RLS ACTIVADO y CERO políticas. Con RLS activo y ninguna política,
-- Postgres deniega todo a los roles anon/authenticated: el CU-05
-- (Solicitar Insumos a Proveedor) fallaría en silencio — listados
-- vacíos e inserts rechazados, sin error visible en la app.
-- Es el mismo problema que arreglamos en la 004 para las otras tablas.
--
-- Reglas aplicadas (informe final):
--   RN03 / RF-INV-06 — aislamiento estricto por restaurante.
--   CU-05            — el actor es el Administrador: solo él genera
--                      órdenes de compra.
--
-- Depende de: 004 (funciones restaurante_actual() y rol_actual()).
-- Es idempotente: DROP POLICY IF EXISTS + CREATE.
-- ============================================================


-- ============================================================
-- 1. proveedores — lectura del tenant; escritura solo Admin
-- ============================================================
ALTER TABLE proveedores ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS proveedores_select_tenant ON proveedores;
CREATE POLICY proveedores_select_tenant ON proveedores
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS proveedores_insert_admin ON proveedores;
CREATE POLICY proveedores_insert_admin ON proveedores
    FOR INSERT WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS proveedores_update_admin ON proveedores;
CREATE POLICY proveedores_update_admin ON proveedores
    FOR UPDATE
    USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    )
    WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS proveedores_delete_admin ON proveedores;
CREATE POLICY proveedores_delete_admin ON proveedores
    FOR DELETE USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );


-- ============================================================
-- 2. pedidos — órdenes de compra al proveedor
--    El WITH CHECK del INSERT valida también que el proveedor sea
--    del mismo restaurante: sin esa condición un Administrador
--    podría emitir una orden contra el proveedor de otro tenant
--    (la FK sola no lo impide).
--    NO se define política de DELETE: según el CU-05 la orden queda
--    documentada a la espera de la mercadería, no se borra.
-- ============================================================
ALTER TABLE pedidos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pedidos_select_tenant ON pedidos;
CREATE POLICY pedidos_select_tenant ON pedidos
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS pedidos_insert_admin ON pedidos;
CREATE POLICY pedidos_insert_admin ON pedidos
    FOR INSERT WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
        AND proveedor_id IN (
            SELECT id FROM proveedores
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

-- UPDATE para mover el estado de la orden (Pendiente -> Recibido).
DROP POLICY IF EXISTS pedidos_update_admin ON pedidos;
CREATE POLICY pedidos_update_admin ON pedidos
    FOR UPDATE
    USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    )
    WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );


-- ============================================================
-- 3. detalle_pedidos — SIN columna restaurante_id.
--    El tenant se deriva del pedido padre, igual que en 'recetas'.
--    Todas las políticas navegan ese join; el INSERT valida además
--    que el insumo sea del mismo restaurante (RF-INV-09).
-- ============================================================
ALTER TABLE detalle_pedidos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS detalle_pedidos_select_tenant ON detalle_pedidos;
CREATE POLICY detalle_pedidos_select_tenant ON detalle_pedidos
    FOR SELECT USING (
        pedido_id IN (
            SELECT id FROM pedidos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

DROP POLICY IF EXISTS detalle_pedidos_insert_admin ON detalle_pedidos;
CREATE POLICY detalle_pedidos_insert_admin ON detalle_pedidos
    FOR INSERT WITH CHECK (
        public.rol_actual() = 'Administrador'
        AND pedido_id IN (
            SELECT id FROM pedidos
            WHERE restaurante_id = public.restaurante_actual()
        )
        AND insumo_id IN (
            SELECT id FROM insumos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

DROP POLICY IF EXISTS detalle_pedidos_update_admin ON detalle_pedidos;
CREATE POLICY detalle_pedidos_update_admin ON detalle_pedidos
    FOR UPDATE
    USING (
        public.rol_actual() = 'Administrador'
        AND pedido_id IN (
            SELECT id FROM pedidos
            WHERE restaurante_id = public.restaurante_actual()
        )
    )
    WITH CHECK (
        public.rol_actual() = 'Administrador'
        AND pedido_id IN (
            SELECT id FROM pedidos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

DROP POLICY IF EXISTS detalle_pedidos_delete_admin ON detalle_pedidos;
CREATE POLICY detalle_pedidos_delete_admin ON detalle_pedidos
    FOR DELETE USING (
        public.rol_actual() = 'Administrador'
        AND pedido_id IN (
            SELECT id FROM pedidos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );
