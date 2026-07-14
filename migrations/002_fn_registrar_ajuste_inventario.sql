-- ============================================================
-- Big Royal SaaS — CU-04: Ajustar Inventario Manualmente
-- ============================================================
-- Funcion RPC transaccional para ajustes manuales de stock.
--
-- Ejecuta, dentro de UNA sola transaccion (atomica):
--   1. Verifica que el insumo exista y pertenezca al restaurante (RN03).
--   2. Bloquea la fila del insumo (FOR UPDATE) para evitar carreras.
--   3. Calcula el nuevo stock a partir de la cantidad con signo.
--   4. Rechaza el ajuste si el stock resultante seria negativo (CU-04, 4.1).
--   5. Actualiza insumos.stock_actual.
--   6. Registra el movimiento en auditoria_inventario (auditoria obligatoria).
--
-- Convencion de signo de p_cantidad_afectada:
--   > 0  -> ingreso / entrada de mercaderia
--   < 0  -> merma / perdida / salida
--
-- Ejecutar este script en el SQL Editor de Supabase (proyecto al que
-- apunta el .env). Es idempotente: usa CREATE OR REPLACE.
-- ============================================================

CREATE OR REPLACE FUNCTION registrar_ajuste_inventario(
    p_restaurante_id   UUID,
    p_insumo_id        UUID,
    p_usuario_id       UUID,
    p_tipo_operacion   TEXT,
    p_cantidad_afectada NUMERIC,
    p_motivo           TEXT
)
RETURNS NUMERIC          -- devuelve el nuevo stock_actual
LANGUAGE plpgsql
AS $$
DECLARE
    v_stock_actual NUMERIC;
    v_nuevo_stock  NUMERIC;
BEGIN
    IF p_cantidad_afectada IS NULL OR p_cantidad_afectada = 0 THEN
        RAISE EXCEPTION 'CANTIDAD_INVALIDA';
    END IF;

    -- RN03: el insumo debe existir y ser del restaurante del usuario.
    SELECT stock_actual
      INTO v_stock_actual
      FROM insumos
     WHERE id = p_insumo_id
       AND restaurante_id = p_restaurante_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'INSUMO_NO_ENCONTRADO';
    END IF;

    v_nuevo_stock := v_stock_actual + p_cantidad_afectada;

    -- CU-04, flujo alterno 4.1: el resultado no puede quedar negativo.
    IF v_nuevo_stock < 0 THEN
        RAISE EXCEPTION 'STOCK_NEGATIVO';
    END IF;

    UPDATE insumos
       SET stock_actual = v_nuevo_stock
     WHERE id = p_insumo_id
       AND restaurante_id = p_restaurante_id;

    INSERT INTO auditoria_inventario (
        restaurante_id, insumo_id, usuario_id,
        tipo_operacion, cantidad_afectada, motivo
    ) VALUES (
        p_restaurante_id, p_insumo_id, p_usuario_id,
        p_tipo_operacion, p_cantidad_afectada, p_motivo
    );

    RETURN v_nuevo_stock;
END;
$$;
