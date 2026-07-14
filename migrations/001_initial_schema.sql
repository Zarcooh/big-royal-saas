-- ============================================================
-- Big Royal SaaS — 001: Esquema base
-- ============================================================
-- REGENERADO el 2026-07-14 a partir del esquema REAL desplegado en
-- Supabase (proyecto saas-big-royal), leyendo el catálogo de Postgres.
--
-- POR QUÉ SE REESCRIBIÓ: la versión anterior de este archivo no
-- correspondía con la base real y era una trampa para quien clonara el
-- repo. Divergencias que tenía:
--   - Inventaba columnas inexistentes (restaurantes.direccion/telefono,
--     insumos.updated_at) y un trigger sobre ese updated_at que, al
--     ejecutarse contra la base real, ROMPÍA todo UPDATE de insumos
--     (CU-02 y CU-04).
--   - Le faltaban 6 de las 8 tablas: proveedores, productos, recetas,
--     auditoria_inventario, pedidos y detalle_pedidos. Alguien las creó
--     a mano desde el SQL Editor y nunca volvieron al repo.
--   - Definía políticas RLS que hoy viven, corregidas, en la 003/004.
--
-- ALCANCE: este archivo crea SOLO las tablas que ya existían en la base
-- antes de que empezáramos a versionar las migraciones. Las demás piezas
-- llegan después, en orden:
--   002 — RPC registrar_ajuste_inventario (CU-04)
--   003 — tabla usuarios (por eso NO está aquí)
--   004 — políticas RLS de los módulos base
--   005 — políticas RLS de abastecimiento (CU-05)
--   006 — tablas ventas/detalle_ventas + RPC registrar_venta (CU-06)
--
-- OJO: aquí se ACTIVA RLS pero todavía no se crean políticas — eso es
-- fiel a la base real, pero significa que una base a medio migrar
-- (001 sin 003/004/005) DENIEGA TODO EN SILENCIO: los listados salen
-- vacíos y los inserts fallan sin error visible. Ejecuta la cadena
-- completa 001 → 006, no te quedes a la mitad.
--
-- Nota sobre integridad: las columnas restaurante_id (y demás claves
-- foráneas) admiten NULL en la base real. Se reproduce tal cual para no
-- divergir de producción, pero conviene saberlo: nada impide a nivel de
-- esquema insertar una fila huérfana sin restaurante.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================================
-- 1. restaurantes — entidad tenant (RN03)
-- ============================================================
CREATE TABLE IF NOT EXISTS restaurantes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre      VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE restaurantes ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 2. proveedores — usados por el CU-05
-- ============================================================
CREATE TABLE IF NOT EXISTS proveedores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id  UUID REFERENCES restaurantes(id) ON DELETE CASCADE,
    nombre          VARCHAR(100) NOT NULL,
    telefono        VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE proveedores ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 3. insumos — catálogo de inventario (CU-02)
-- ============================================================
CREATE TABLE IF NOT EXISTS insumos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id  UUID REFERENCES restaurantes(id) ON DELETE CASCADE,
    nombre          VARCHAR(100) NOT NULL,
    unidad          VARCHAR(20) NOT NULL,
    stock_actual    NUMERIC(10, 2) DEFAULT 0,
    stock_minimo    NUMERIC(10, 2) DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE insumos ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 4. productos — platillos del menú; 'precio' alimenta el total de venta
-- ============================================================
CREATE TABLE IF NOT EXISTS productos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id  UUID REFERENCES restaurantes(id) ON DELETE CASCADE,
    nombre          VARCHAR(100) NOT NULL,
    precio          NUMERIC(10, 2) DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE productos ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 5. recetas — cuánto insumo consume cada unidad vendida (CU-03)
--    SIN columna restaurante_id: el tenant se deriva del producto.
--    El UNIQUE implementa la validación de duplicados del CU-03
--    (RF-INV-10): un insumo no puede repetirse en la misma receta.
-- ============================================================
CREATE TABLE IF NOT EXISTS recetas (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    producto_id       UUID REFERENCES productos(id) ON DELETE CASCADE,
    insumo_id         UUID REFERENCES insumos(id) ON DELETE CASCADE,
    cantidad_consumo  NUMERIC(10, 4) NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (producto_id, insumo_id)
);

ALTER TABLE recetas ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 6. auditoria_inventario — log inmutable de movimientos de stock
--    Lo escriben las dos RPC: registrar_ajuste_inventario (002) y
--    registrar_venta (006). Convención de signo: positivo suma stock
--    (ingreso), negativo lo resta (merma, pérdida, venta).
--    'tipo_operacion' es texto libre, sin CHECK.
-- ============================================================
CREATE TABLE IF NOT EXISTS auditoria_inventario (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id     UUID REFERENCES restaurantes(id) ON DELETE CASCADE,
    insumo_id          UUID REFERENCES insumos(id) ON DELETE CASCADE,
    usuario_id         UUID,
    tipo_operacion     VARCHAR(50) NOT NULL,
    cantidad_afectada  NUMERIC(10, 2) NOT NULL,
    motivo             TEXT,
    fecha              TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE auditoria_inventario ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 7. pedidos — órdenes de compra al proveedor (CU-05)
--    'estado' arranca en PENDIENTE, como pide el CU-05.
-- ============================================================
CREATE TABLE IF NOT EXISTS pedidos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurante_id  UUID REFERENCES restaurantes(id) ON DELETE CASCADE,
    proveedor_id    UUID REFERENCES proveedores(id) ON DELETE CASCADE,
    estado          VARCHAR(30) DEFAULT 'PENDIENTE',
    fecha_creacion  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE pedidos ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 8. detalle_pedidos — líneas de la orden de compra (CU-05)
--    SIN columna restaurante_id: el tenant se deriva del pedido padre.
-- ============================================================
CREATE TABLE IF NOT EXISTS detalle_pedidos (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id  UUID REFERENCES pedidos(id) ON DELETE CASCADE,
    insumo_id  UUID REFERENCES insumos(id) ON DELETE CASCADE,
    cantidad   NUMERIC(10, 2) NOT NULL
);

ALTER TABLE detalle_pedidos ENABLE ROW LEVEL SECURITY;
