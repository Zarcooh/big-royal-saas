-- ============================================================
-- Big Royal SaaS — CU-01: Auditoría de Ingreso (login)
-- ============================================================
-- Materializa el paso `registrarIngreso()` del diagrama de
-- secuencia CU-01 (c_IniciarSesion -> e_LogAuditoria): cada inicio
-- de sesión exitoso deja un registro inmutable de acceso.
--
-- La auditoría de accesos se separa de auditoria_inventario porque
-- son eventos distintos: aquella registra movimientos de stock (con
-- insumo y cantidad), esta registra ingresos de usuarios.
--
-- La escritura ocurre por la RPC registrar_ingreso() (SECURITY
-- DEFINER), única puerta de inserción, igual que 'ventas' en la
-- migración 006. El log es de solo-inserción (inmutable).
--
-- REQUISITOS PREVIOS:
--   - migrations/003 (tabla 'usuarios') y 004 (restaurante_actual()).
--
-- Es idempotente: usa CREATE TABLE IF NOT EXISTS, CREATE OR REPLACE
-- y DROP POLICY IF EXISTS. Ejecutar en el SQL Editor del proyecto
-- del .env.
-- ============================================================


-- ============================================================
-- 1. Tabla auditoria_accesos — log inmutable de ingresos
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria_accesos (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id     UUID NOT NULL REFERENCES usuarios(id),
    restaurante_id UUID NOT NULL REFERENCES restaurantes(id),
    fecha          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS auditoria_accesos_restaurante_fecha_idx
    ON auditoria_accesos (restaurante_id, fecha DESC);


-- ============================================================
-- 2. RLS — lectura por tenant; sin INSERT/UPDATE/DELETE.
--    El log es inmutable y solo lo escribe la RPC SECURITY DEFINER.
-- ============================================================
ALTER TABLE auditoria_accesos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS auditoria_accesos_select_tenant ON auditoria_accesos;
CREATE POLICY auditoria_accesos_select_tenant ON auditoria_accesos
    FOR SELECT USING (restaurante_id = public.restaurante_actual());


-- ============================================================
-- 3. RPC registrar_ingreso() — SECURITY DEFINER.
--    Deriva usuario y restaurante desde auth.uid() (el token), no de
--    parámetros. Es SECURITY DEFINER porque el login lo hacen ambos
--    roles (Administrador y Cajero); así se evita depender de una
--    política INSERT y de que el rol sea Administrador.
-- ============================================================
CREATE OR REPLACE FUNCTION public.registrar_ingreso()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_usuario_id     UUID;
    v_restaurante_id UUID;
    v_id             UUID;
BEGIN
    v_usuario_id := auth.uid();
    IF v_usuario_id IS NULL THEN
        RAISE EXCEPTION 'NO_AUTENTICADO';
    END IF;

    SELECT restaurante_id
      INTO v_restaurante_id
      FROM usuarios
     WHERE id = v_usuario_id;

    IF v_restaurante_id IS NULL THEN
        RAISE EXCEPTION 'USUARIO_SIN_PERFIL';
    END IF;

    INSERT INTO auditoria_accesos (usuario_id, restaurante_id)
    VALUES (v_usuario_id, v_restaurante_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.registrar_ingreso() TO authenticated;
