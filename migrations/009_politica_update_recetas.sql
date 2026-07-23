-- ============================================================
-- Big Royal SaaS — Migración 009: UPDATE sobre recetas (CU-03)
-- ============================================================
-- La 004 dio a 'recetas' políticas de SELECT, INSERT y DELETE, pero no de
-- UPDATE: cuando se escribió, la receta solo se podía armar y deshacer, no
-- corregir. Al agregar "editar la cantidad de consumo" hace falta esta
-- política; sin ella el UPDATE no da error, simplemente no afecta ninguna
-- fila (así se comporta RLS), y la corrección se pierde en silencio.
--
-- Mismo criterio que las otras tres: 'recetas' no tiene restaurante_id, así
-- que el tenant se deriva navegando hasta productos.restaurante_id, y la
-- RN02 reserva la operación al Administrador.
--
-- El USING decide qué filas puede tocar; el WITH CHECK, cómo pueden quedar.
-- Ambos son necesarios: sin WITH CHECK, un UPDATE podría mover una línea de
-- receta al producto de otro restaurante.
--
-- Depende de: 004 (restaurante_actual() / rol_actual()).
-- Es idempotente: DROP POLICY IF EXISTS + CREATE.
-- ============================================================

DROP POLICY IF EXISTS recetas_update_admin ON recetas;
CREATE POLICY recetas_update_admin ON recetas
    FOR UPDATE USING (
        public.rol_actual() = 'Administrador'
        AND producto_id IN (
            SELECT id FROM productos
            WHERE restaurante_id = public.restaurante_actual()
        )
    )
    WITH CHECK (
        public.rol_actual() = 'Administrador'
        AND producto_id IN (
            SELECT id FROM productos
            WHERE restaurante_id = public.restaurante_actual()
        )
    );
