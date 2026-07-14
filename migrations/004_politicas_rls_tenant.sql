-- ============================================================
-- Big Royal SaaS — Migración 004: Políticas RLS multi-tenant
-- ============================================================
-- CONTEXTO: Las tablas del proyecto tienen RLS ACTIVADO pero sin
-- ninguna política (verificado: todo insert anónimo devuelve
-- 42501). Con RLS activo y cero políticas, la BD deniega todo a
-- los roles anon/authenticated, así que CU-02/03/04 fallan en
-- silencio (listados vacíos, inserts con error) aunque el login
-- funcione.
--
-- Esta migración crea el conjunto completo de políticas de tenant
-- (RN03): cada usuario solo ve/opera sobre datos de SU restaurante,
-- y las escrituras quedan restringidas a rol 'Administrador'.
--
-- REQUISITOS PREVIOS:
--   - Ejecutar antes migrations/003 (crea la tabla 'usuarios').
--   - La RPC de migrations/002 NO es SECURITY DEFINER: corre con
--     los permisos del llamante, por eso necesita las políticas de
--     UPDATE en insumos e INSERT en auditoria_inventario de abajo.
--
-- Es idempotente: usa DROP POLICY IF EXISTS + CREATE.
-- Ejecutar en el SQL Editor del proyecto del .env (mtogjgipqbzfphuqysag).
-- ============================================================


-- ============================================================
-- 1. Funciones auxiliares (SECURITY DEFINER)
--    Resuelven el restaurante y el rol del usuario en sesión sin
--    disparar RLS sobre 'usuarios' (evita recursión) y hacen las
--    políticas legibles y rápidas.
-- ============================================================
CREATE OR REPLACE FUNCTION public.restaurante_actual()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT restaurante_id FROM usuarios WHERE id = auth.uid()
$$;

CREATE OR REPLACE FUNCTION public.rol_actual()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT rol FROM usuarios WHERE id = auth.uid()
$$;

GRANT EXECUTE ON FUNCTION public.restaurante_actual() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.rol_actual() TO anon, authenticated;


-- ============================================================
-- 2. usuarios — cada quien lee solo su propio registro
--    (definido en la 003, se re-asegura aquí por idempotencia)
-- ============================================================
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS usuarios_select_own ON usuarios;
CREATE POLICY usuarios_select_own ON usuarios
    FOR SELECT USING (id = auth.uid());


-- ============================================================
-- 3. restaurantes — el usuario ve solo su propio restaurante
-- ============================================================
ALTER TABLE restaurantes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS restaurantes_select_tenant ON restaurantes;
CREATE POLICY restaurantes_select_tenant ON restaurantes
    FOR SELECT USING (id = public.restaurante_actual());


-- ============================================================
-- 4. insumos — lectura para el tenant; escritura solo Admin
-- ============================================================
ALTER TABLE insumos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS insumos_select_tenant ON insumos;
CREATE POLICY insumos_select_tenant ON insumos
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS insumos_insert_admin ON insumos;
CREATE POLICY insumos_insert_admin ON insumos
    FOR INSERT WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS insumos_update_admin ON insumos;
CREATE POLICY insumos_update_admin ON insumos
    FOR UPDATE
    USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    )
    WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS insumos_delete_admin ON insumos;
CREATE POLICY insumos_delete_admin ON insumos
    FOR DELETE USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );


-- ============================================================
-- 5. productos — lectura para el tenant; escritura solo Admin
-- ============================================================
ALTER TABLE productos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS productos_select_tenant ON productos;
CREATE POLICY productos_select_tenant ON productos
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS productos_insert_admin ON productos;
CREATE POLICY productos_insert_admin ON productos
    FOR INSERT WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS productos_update_admin ON productos;
CREATE POLICY productos_update_admin ON productos
    FOR UPDATE
    USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    )
    WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );

DROP POLICY IF EXISTS productos_delete_admin ON productos;
CREATE POLICY productos_delete_admin ON productos
    FOR DELETE USING (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );


-- ============================================================
-- 6. recetas — SIN columna restaurante_id (RN03 / RF-INV-09).
--    El tenant se deriva del producto: recetas.producto_id ->
--    productos.restaurante_id. Todas las políticas navegan ese join.
-- ============================================================
ALTER TABLE recetas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS recetas_select_tenant ON recetas;
CREATE POLICY recetas_select_tenant ON recetas
    FOR SELECT USING (
        producto_id IN (
            SELECT id FROM productos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

DROP POLICY IF EXISTS recetas_insert_admin ON recetas;
CREATE POLICY recetas_insert_admin ON recetas
    FOR INSERT WITH CHECK (
        public.rol_actual() = 'Administrador'
        AND producto_id IN (
            SELECT id FROM productos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );

DROP POLICY IF EXISTS recetas_delete_admin ON recetas;
CREATE POLICY recetas_delete_admin ON recetas
    FOR DELETE USING (
        public.rol_actual() = 'Administrador'
        AND producto_id IN (
            SELECT id FROM productos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );


-- ============================================================
-- 7. auditoria_inventario — lectura del tenant; alta solo Admin.
--    La escribe la RPC registrar_ajuste_inventario (no SECURITY
--    DEFINER), por eso necesita política de INSERT aquí.
--    NO se definen UPDATE/DELETE: el log de auditoría es inmutable.
-- ============================================================
ALTER TABLE auditoria_inventario ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS auditoria_select_tenant ON auditoria_inventario;
CREATE POLICY auditoria_select_tenant ON auditoria_inventario
    FOR SELECT USING (restaurante_id = public.restaurante_actual());

DROP POLICY IF EXISTS auditoria_insert_admin ON auditoria_inventario;
CREATE POLICY auditoria_insert_admin ON auditoria_inventario
    FOR INSERT WITH CHECK (
        restaurante_id = public.restaurante_actual()
        AND public.rol_actual() = 'Administrador'
    );
