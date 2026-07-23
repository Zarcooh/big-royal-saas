-- ============================================================
-- Big Royal SaaS — Migración 008: venta con varios productos
-- (CU-06: Registrar Venta, carrito del Cajero) — RF-INV-40, RN01, RNF-REL-01
-- ============================================================
-- registrar_venta() (006) resuelve UN producto por llamada. El carrito del
-- Cajero necesita cobrar varios productos en un solo comprobante, y hacerlo
-- llamando N veces a la RPC anterior produciría N ventas independientes: si
-- el tercer producto se queda sin stock, los dos primeros ya estarían
-- cobrados y descontados. Esta función registra TODO el carrito dentro de
-- una sola transacción, así que o pasa la compra entera o no pasa nada
-- (RNF-REL-01).
--
-- No reemplaza a registrar_venta(): esa sigue siendo la puerta de entrada de
-- la venta rápida de un producto. Ambas comparten las mismas garantías.
--
-- Depende de: 004 (usuarios/rol), 006 (tablas ventas y detalle_ventas).
-- Es idempotente: CREATE OR REPLACE.
-- ============================================================

-- p_items llega como JSON desde la app:
--   [{"producto_id": "uuid", "cantidad": 2}, ...]
-- Se usa JSONB y no dos arrays paralelos para que la app no pueda mandar
-- listas de distinto largo y desalinear producto con cantidad.
CREATE OR REPLACE FUNCTION public.registrar_venta_multiple(
    p_items                JSONB,
    p_confirmar_sin_receta BOOLEAN DEFAULT FALSE
)
RETURNS UUID                     -- id de la venta registrada
LANGUAGE plpgsql
SECURITY DEFINER                 -- mismo motivo que en 006: el Cajero no
SET search_path = public         -- tiene (ni debe tener) UPDATE sobre insumos
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
    v_consumo        RECORD;   -- no se llama 'r': ese nombre choca
                               -- con el alias de la tabla recetas en
                               -- los subselects de abajo, y plpgsql
                               -- resuelve a favor de la variable.
BEGIN
    IF v_usuario_id IS NULL THEN
        RAISE EXCEPTION 'NO_AUTENTICADO';
    END IF;

    IF p_items IS NULL OR jsonb_typeof(p_items) <> 'array'
       OR jsonb_array_length(p_items) = 0 THEN
        RAISE EXCEPTION 'CARRITO_VACIO';
    END IF;

    -- Membresía del llamante: al ser SECURITY DEFINER, no hay RLS detrás.
    -- Las comprobaciones de tenant de abajo son la ÚNICA barrera.
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

    -- Las líneas del carrito se normalizan siempre con el mismo CTE 'items':
    -- un producto puede venir repetido si el Cajero lo agregó dos veces, y
    -- consolidarlo evita duplicar líneas de detalle. No se usa una tabla
    -- temporal a propósito: bajo SET search_path esta función no debe
    -- depender de la resolución implícita del esquema pg_temp.
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
           -- RN03: producto inexistente y producto de otro restaurante dan el
           -- mismo error, para no revelar qué vende la competencia.
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

    -- CU-06, flujo alterno 2.1: si algún producto del carrito no tiene
    -- receta, se avisa al Cajero antes de continuar. Si confirma, la app
    -- vuelve a llamar con p_confirmar_sin_receta => true.
    IF v_sin_receta > 0 AND NOT p_confirmar_sin_receta THEN
        RAISE EXCEPTION 'PRODUCTO_SIN_RECETA';
    END IF;

    -- El precio sale de la base, nunca del carrito: el Cajero no fija precios.
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

    -- precio_unitario es una FOTO del precio de hoy (ver nota en 006).
    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario)
    SELECT v_venta_id, i.producto_id, i.cantidad, coalesce(p.precio, 0)
      FROM (
          SELECT it.producto_id, sum(it.cantidad) AS cantidad
            FROM jsonb_to_recordset(p_items)
              AS it(producto_id UUID, cantidad NUMERIC)
           GROUP BY it.producto_id
      ) i
      JOIN productos p ON p.id = i.producto_id;

    -- RN01: auto-descuento por receta.
    -- El consumo se AGREGA por insumo antes de descontar: si dos productos
    -- del carrito llevan el mismo insumo, se valida el stock contra el total
    -- requerido y no contra cada línea por separado (dos descuentos de 6 que
    -- pasan sueltos pueden dejar el stock en negativo si solo hay 10).
    -- El ORDER BY insumo_id fija un orden de bloqueo estable entre cajas
    -- simultáneas para evitar abrazos mortales (deadlock).
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

            -- Auditoría: negativo porque la venta resta stock, misma
            -- convención de signo que registrar_ajuste_inventario.
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

-- Al ser SECURITY DEFINER, un GRANT a 'anon' sería una puerta abierta para
-- escribir en insumos sin sesión.
REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB, BOOLEAN) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.registrar_venta_multiple(JSONB, BOOLEAN) FROM anon;
GRANT EXECUTE ON FUNCTION public.registrar_venta_multiple(JSONB, BOOLEAN) TO authenticated;
