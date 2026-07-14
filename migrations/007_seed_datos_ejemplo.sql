-- ============================================================
-- Big Royal SaaS — 007: Datos de ejemplo (SEED)
-- ============================================================
-- OPCIONAL. No es parte del esquema: son datos de demo para poder
-- probar CU-03 (recetas), CU-04 (ajustes) y CU-06 (venta con
-- auto-descuento) sin tener que cargar todo a mano.
--
-- NO ejecutar en un entorno real de producción.
--
-- Depende de: la cadena 001 → 006 aplicada, y del restaurante
-- 'Big Royal Centro' (id 1111...1111) creado en el seed inicial.
--
-- Es idempotente: usa IDs fijos + ON CONFLICT DO NOTHING, así que
-- puede ejecutarse varias veces sin duplicar nada.
--
-- Los stocks están puestos con holgura para que se puedan registrar
-- varias ventas seguidas y ver bajar el inventario. La lechuga es la
-- excepción a propósito: tiene poco stock, para que sea fácil provocar
-- el error STOCK_INSUFICIENTE y comprobar que la venta se revierte
-- entera (flujo alterno 4.1 del CU-06).
-- ============================================================


-- ============================================================
-- 1. Insumos (CU-02)
-- ============================================================
INSERT INTO insumos (id, restaurante_id, nombre, unidad, stock_actual, stock_minimo) VALUES
    ('10000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Carne de res',        'kg',     20.00,  5.00),
    ('10000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'Pan de hamburguesa',  'unidad', 100.00, 20.00),
    ('10000000-0000-0000-0000-000000000003', '11111111-1111-1111-1111-111111111111', 'Queso cheddar',       'unidad', 80.00,  15.00),
    ('10000000-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111', 'Lechuga',             'kg',     0.50,   1.00),
    ('10000000-0000-0000-0000-000000000005', '11111111-1111-1111-1111-111111111111', 'Tomate',              'kg',     6.00,   1.00),
    ('10000000-0000-0000-0000-000000000006', '11111111-1111-1111-1111-111111111111', 'Papa',                'kg',     30.00,  5.00),
    ('10000000-0000-0000-0000-000000000007', '11111111-1111-1111-1111-111111111111', 'Aceite',              'L',      10.00,  2.00),
    ('10000000-0000-0000-0000-000000000008', '11111111-1111-1111-1111-111111111111', 'Gaseosa 500 ml',      'unidad', 48.00,  12.00)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 2. Productos del menú
--    'Postre del día' se deja A PROPÓSITO sin receta, para poder
--    probar el flujo alterno 2.1 del CU-06 (el sistema avisa al
--    Cajero antes de continuar).
-- ============================================================
INSERT INTO productos (id, restaurante_id, nombre, precio) VALUES
    ('20000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Hamburguesa Royal',  15.00),
    ('20000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'Hamburguesa Doble',  22.00),
    ('20000000-0000-0000-0000-000000000003', '11111111-1111-1111-1111-111111111111', 'Papas Fritas',        7.00),
    ('20000000-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111', 'Gaseosa 500 ml',      4.00),
    ('20000000-0000-0000-0000-000000000005', '11111111-1111-1111-1111-111111111111', 'Postre del día',      6.00)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 3. Recetas (CU-03) — cuánto insumo consume CADA UNIDAD vendida.
--    Esto es lo que lee registrar_venta para el auto-descuento (RN01).
-- ============================================================
INSERT INTO recetas (producto_id, insumo_id, cantidad_consumo) VALUES
    -- Hamburguesa Royal
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 0.1500),  -- carne
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000002', 1.0000),  -- pan
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000003', 1.0000),  -- queso
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000004', 0.0200),  -- lechuga
    ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000005', 0.0300),  -- tomate

    -- Hamburguesa Doble: el doble de carne y de queso
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 0.3000),
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 1.0000),
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000003', 2.0000),
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000004', 0.0200),
    ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000005', 0.0300),

    -- Papas Fritas
    ('20000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000006', 0.2000),  -- papa
    ('20000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000007', 0.0500),  -- aceite

    -- Gaseosa: consume una unidad de su propio insumo
    ('20000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000008', 1.0000)

    -- 'Postre del día' no lleva receta a propósito (ver nota arriba).
ON CONFLICT (producto_id, insumo_id) DO NOTHING;


-- ============================================================
-- 4. Proveedor de ejemplo (para el CU-05)
-- ============================================================
INSERT INTO proveedores (id, restaurante_id, nombre, telefono) VALUES
    ('40000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Distribuidora La Merced', '944123456'),
    ('40000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'Avícola El Trigal',       '955987654')
ON CONFLICT (id) DO NOTHING;
