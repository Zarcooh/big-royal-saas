-- ============================================================
-- Big Royal SaaS — Migración 003: crear tabla 'usuarios'
-- ============================================================
-- CONTEXTO: la base del proyecto se creó a mano sin la tabla
-- 'usuarios'. Sin ella el login de CU-01 falla, porque auth.py
-- consulta 'usuarios' para obtener restaurante_id y rol.
--
-- Por eso 'usuarios' NO está en la 001: esa migración refleja el
-- esquema base tal como existía (8 tablas, sin usuarios), y esta
-- la añade encima. Ejecuta la cadena completa 001 → 006.
--
-- Ejecutar en el SQL Editor de Supabase del proyecto correcto
-- (el mismo del .env: mtogjgipqbzfphuqysag).
-- ============================================================

-- Vincula un usuario de Supabase Auth con un restaurante y un rol.
CREATE TABLE IF NOT EXISTS usuarios (
    id              UUID PRIMARY KEY,          -- Debe coincidir con auth.users.id
    restaurante_id  UUID NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    rol             VARCHAR(50) NOT NULL CHECK (rol IN ('Administrador', 'Cajero')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;

-- Política: cada usuario solo puede leer su propio registro.
DROP POLICY IF EXISTS usuarios_select_own ON usuarios;
CREATE POLICY usuarios_select_own ON usuarios
    FOR SELECT
    USING (id = auth.uid());


-- ============================================================
-- SEED (opcional) — datos mínimos para poder iniciar sesión.
-- Descomentar y completar tras crear el usuario en Auth.
-- ============================================================
-- 1) En el dashboard: Authentication → Users → "Add user",
--    crea el usuario (email + password) y copia su UUID.
--
-- 2) Crea un restaurante y vincula ese UUID como Administrador:
--
-- INSERT INTO restaurantes (id, nombre)
-- VALUES ('11111111-1111-1111-1111-111111111111', 'Big Royal Centro')
-- ON CONFLICT (id) DO NOTHING;
--
-- INSERT INTO usuarios (id, restaurante_id, rol)
-- VALUES (
--     '<UUID-del-usuario-de-Auth>',
--     '11111111-1111-1111-1111-111111111111',
--     'Administrador'
-- );
