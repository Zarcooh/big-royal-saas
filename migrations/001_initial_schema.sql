-- ============================================================
-- Big Royal SaaS — Esquema Inicial de Base de Datos
-- ============================================================
-- Este script debe ejecutarse en el SQL Editor de Supabase.
-- Crea las tablas necesarias para los CU-01 y CU-02,
-- aplicando Row Level Security (RLS) para el aislamiento
-- cross-tenant (RN03).

-- ============================================================
-- 1. Extensión para UUIDs
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- 2. Tabla: restaurantes
-- ============================================================
CREATE TABLE IF NOT EXISTS restaurantes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre      VARCHAR(200) NOT NULL,
    direccion   TEXT,
    telefono    VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Habilitar RLS
ALTER TABLE restaurantes ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 3. Tabla: usuarios
--    Vincula un usuario de Supabase Auth con un restaurante y un rol.
-- ============================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id              UUID PRIMARY KEY,          -- Debe coincidir con auth.users.id
    restaurante_id  UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    rol             VARCHAR(50) NOT NULL CHECK (rol IN ('Administrador', 'Cajero')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- Política: cada usuario solo puede leer su propio registro
CREATE POLICY usuarios_select_own ON usuarios
    FOR SELECT
    USING (id = auth.uid());


-- ============================================================
-- 4. Tabla: insumos
--    Columnas exactas: id, restaurante_id, nombre, unidad,
--                      stock_actual, stock_minimo
-- ============================================================
CREATE TABLE IF NOT EXISTS insumos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id  UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    nombre          VARCHAR(150) NOT NULL,
    unidad          VARCHAR(50)  NOT NULL,
    stock_actual    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    stock_minimo    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE insumos ENABLE ROW LEVEL SECURITY;

-- Política: solo miembros del mismo restaurante pueden ver los insumos
CREATE POLICY insumos_select_tenant ON insumos
    FOR SELECT
    USING (
        restaurante_id IN (
            SELECT u.restaurante_id
            FROM usuarios u
            WHERE u.id = auth.uid()
        )
    );

-- Política: solo Administradores del mismo restaurante pueden insertar
CREATE POLICY insumos_insert_admin ON insumos
    FOR INSERT
    WITH CHECK (
        restaurante_id IN (
            SELECT u.restaurante_id
            FROM usuarios u
            WHERE u.id = auth.uid() AND u.rol = 'Administrador'
        )
    );

-- Política: solo Administradores del mismo restaurante pueden actualizar
CREATE POLICY insumos_update_admin ON insumos
    FOR UPDATE
    USING (
        restaurante_id IN (
            SELECT u.restaurante_id
            FROM usuarios u
            WHERE u.id = auth.uid() AND u.rol = 'Administrador'
        )
    )
    WITH CHECK (
        restaurante_id IN (
            SELECT u.restaurante_id
            FROM usuarios u
            WHERE u.id = auth.uid() AND u.rol = 'Administrador'
        )
    );

-- Política: solo Administradores del mismo restaurante pueden eliminar
CREATE POLICY insumos_delete_admin ON insumos
    FOR DELETE
    USING (
        restaurante_id IN (
            SELECT u.restaurante_id
            FROM usuarios u
            WHERE u.id = auth.uid() AND u.rol = 'Administrador'
        )
    );


-- ============================================================
-- 5. Función para actualizar updated_at automáticamente
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON insumos
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


-- ============================================================
-- 6. Insertar datos de prueba (opcional)
-- ============================================================
-- NOTA: Primero debes crear los usuarios en Supabase Auth
-- y luego insertar los registros en 'usuarios' manualmente.

-- INSERT INTO restaurantes (id, nombre) VALUES
--     ('11111111-1111-1111-1111-111111111111', 'Big Royal Centro'),
--     ('22222222-2222-2222-2222-222222222222', 'Big Royal Norte');
