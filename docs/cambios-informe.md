# Cambios para el informe final — Big Royal SaaS

Resumen de lo implementado en la rama `feature/mejoras-carrito-recetas-reportes`
(PR #5 → `develop`), alineado con la numeración de casos de uso del equipo.

**Puntos clave:**
- **No se agregaron tablas** a la base de datos (siguen siendo 12).
- Se agregaron 1 función RPC y 1 política RLS (migraciones 008 y 009).
- **No se agregaron requisitos no funcionales nuevos**; los existentes
  (RNF-REL-01 atomicidad, RN01, RN02, RN03) se respetaron y en un caso se
  ampliaron de alcance.
- Los `RF-INV-XX` van como **propuestos**: ajusta la numeración a tu esquema.

---

## 1. Casos de uso NUEVOS — Gestión de Productos (CU-22 a CU-25)

Hasta ahora los productos solo se creaban desde el *seed* (SQL); no había ningún
CU que cubriera su gestión, pese a que las recetas (CU-06..12) y la venta
(CU-15) dependen de que existan productos. Estos cuatro CU cubren ese vacío,
siguiendo el mismo patrón que los de Insumos (CU-02..05).

### CU-22. Listar Productos
- **Actor:** Administrador.
- **Descripción:** Muestra el catálogo de productos del restaurante con su
  precio y el estado de su receta (cuántos insumos tiene o "sin receta").
- **Precondición:** El Administrador ha iniciado sesión.
- **Flujo básico:**
  1. El Administrador abre "Recetas".
  2. El sistema lista los productos de su restaurante, ordenados por nombre.
  3. Opcionalmente escribe un texto para filtrar por nombre.
- **Reglas:** RN03 (solo productos del restaurante en sesión); el filtro por
  nombre se aplica después del filtro de tenant.
- **RF propuesto:** El sistema permite listar y filtrar por nombre los productos
  del restaurante, indicando el estado de su receta.

### CU-23. Agregar Producto
- **Actor:** Administrador.
- **Descripción:** Crea un producto con nombre y precio de venta.
- **Precondición:** El Administrador ha iniciado sesión.
- **Flujo básico:**
  1. El Administrador pulsa "+ Nuevo Producto".
  2. Ingresa nombre y precio y guarda.
  3. El sistema crea el producto y lleva directamente a gestionar su receta.
- **Validaciones:** nombre obligatorio; precio numérico ≥ 0.
- **Reglas:** RN03 (el producto se crea con el restaurante_id de la sesión).
- **RF propuesto:** El sistema permite crear un producto (nombre y precio).

### CU-24. Editar Producto
- **Actor:** Administrador.
- **Descripción:** Modifica el nombre y el precio de un producto.
- **Precondición:** El producto existe y pertenece al restaurante en sesión.
- **Flujo básico:**
  1. El Administrador pulsa "Editar" en la fila del producto.
  2. Cambia nombre y/o precio y guarda.
- **Validaciones:** nombre obligatorio; precio numérico ≥ 0.
- **Reglas:** el cambio de precio **no** altera el historial: cada venta guarda
  el precio con el que se vendió (foto del precio en `detalle_ventas`).
- **RF propuesto:** El sistema permite editar el nombre y el precio de un
  producto sin afectar el precio ya registrado en ventas anteriores.

### CU-25. Eliminar Producto
- **Actor:** Administrador.
- **Descripción:** Elimina un producto y, en cascada, su receta.
- **Precondición:** El producto existe y pertenece al restaurante en sesión.
- **Flujo básico:**
  1. El Administrador pulsa "Eliminar" en la fila del producto y confirma.
  2. El sistema elimina el producto y las líneas de su receta.
- **Flujo alterno:** si el producto tiene ventas registradas, el sistema
  **rechaza** el borrado y avisa (protege el historial que usan los reportes).
- **Reglas:** RN03; el borrado de la receta se apoya en el `ON DELETE CASCADE`
  de `recetas.producto_id`.
- **RF propuesto:** El sistema permite eliminar un producto sin ventas
  registradas, eliminando en cascada su receta.

---

## 2. Casos de uso EXISTENTES — redacción actualizada / implementados

### CU-02. Listar Insumos
- **Actor:** Administrador.
- **Descripción:** Lista los insumos del restaurante con su stock actual y
  mínimo, resaltando los que están en o bajo el mínimo, con buscador por nombre.
- **Precondición:** El Administrador ha iniciado sesión.
- **Flujo básico:**
  1. El Administrador abre "Insumos".
  2. El sistema lista los insumos de su restaurante ordenados por nombre y marca
     en rojo los que tienen stock ≤ stock mínimo.
  3. (Opcional) escribe un texto y pulsa "Buscar"; el sistema filtra por nombre.
     "Limpiar" restaura la lista completa.
- **Reglas:** RN03 (solo insumos del restaurante); el filtro por nombre se
  aplica después del filtro de tenant.
- **RF propuesto:** El sistema permite filtrar el catálogo de insumos por nombre
  (búsqueda parcial, sin distinguir mayúsculas).

### CU-06. Listar Recetas
- **Actor:** Administrador.
- **Descripción:** Se presenta como el catálogo de productos (CU-22): punto de
  entrada para ver y gestionar la receta de cada producto.
- **Precondición:** El Administrador ha iniciado sesión.
- **Flujo básico:**
  1. El Administrador abre "Recetas".
  2. El sistema lista los productos con su precio y el estado de su receta
     (cuántos insumos tiene o "sin receta").
  3. Pulsa "Gestionar receta" en un producto para ver y modificar su receta
     (CU-08, CU-10, CU-11, CU-12).
- **Reglas:** RN03.

### CU-08. Eliminar Receta
- **Actor:** Administrador.
- **Descripción:** Elimina todas las líneas de la receta de un producto, sin
  borrar el producto.
- **Precondición:** El producto pertenece al restaurante en sesión y tiene al
  menos un insumo en su receta.
- **Flujo básico:**
  1. En "Gestionar receta", el Administrador pulsa "Eliminar receta completa" y
     confirma.
  2. El sistema borra todas las líneas de la receta.
  3. El producto sigue existiendo, pero venderlo ya no descuenta stock (queda
     como caso "producto sin receta" del CU-15).
- **Reglas:** RN03 (el tenant se valida a través del producto).

### CU-10. Agregar Insumo a Receta
- **Actor:** Administrador.
- **Descripción:** Agrega un insumo a la receta de un producto con su cantidad
  de consumo por unidad vendida.
- **Precondición:** El producto pertenece al restaurante y queda al menos un
  insumo no incluido en su receta.
- **Flujo básico:**
  1. En "Gestionar receta", el Administrador elige un insumo del desplegable e
     ingresa la cantidad de consumo.
  2. Pulsa "Agregar".
  3. El sistema valida y agrega la línea a la receta.
- **Flujo alterno:** si el insumo ya está en la receta, el sistema avisa y no lo
  duplica (RF-INV-10).
- **Validaciones:** el insumo debe existir y ser del restaurante (RF-INV-09); la
  cantidad de consumo debe ser mayor que cero.

### CU-11. Eliminar Insumo de Receta
- **Actor:** Administrador.
- **Descripción:** Quita un insumo de la receta de un producto.
- **Precondición:** El insumo forma parte de la receta del producto.
- **Flujo básico:**
  1. En "Gestionar receta", el Administrador pulsa "Eliminar" en la fila del
     insumo y confirma.
  2. El sistema quita esa línea de la receta.
- **Reglas:** RN03 (la línea se acota al producto ya validado).

### CU-12. Editar Insumo de Receta
- **Actor:** Administrador.
- **Descripción:** Modifica la cantidad de consumo de un insumo ya presente en
  la receta.
- **Precondición:** El insumo forma parte de la receta del producto.
- **Flujo básico:**
  1. En "Gestionar receta", el Administrador cambia la cantidad en la fila del
     insumo y pulsa "Guardar".
  2. El sistema actualiza la cantidad de consumo.
- **Validaciones:** la cantidad debe ser mayor que cero.
- **Nota BD:** requirió agregar la política RLS de UPDATE sobre `recetas`
  (`recetas_update_admin`, **migración 009**); sin ella la edición fallaba en
  silencio.

### CU-15. Registrar Venta
- **Actor:** Cajero.
- **Descripción:** El Cajero arma un pedido con **uno o varios productos**
  (carrito en sesión) y lo confirma en un solo comprobante, disparando el
  auto-descuento de stock (CU-16).
- **Precondición:** El Cajero ha iniciado sesión y existen productos.
- **Flujo básico:**
  1. El Cajero abre "Registrar Venta".
  2. En el catálogo indica la cantidad y pulsa "+ Agregar" por cada producto; el
     ítem se suma al detalle del pedido.
  3. Ajusta cantidades ("Actualizar") o quita ítems del carrito.
  4. Pulsa "Confirmar compra".
  5. El sistema registra la venta, descuenta el stock (CU-16) y muestra el
     comprobante con el detalle de productos y el stock actualizado.
- **Flujo alterno 2.1 (producto sin receta):** si algún producto no tiene receta,
  el sistema avisa y ofrece "Continuar de todos modos"; al confirmar, esa parte
  se registra sin descontar stock.
- **Flujo alterno (stock insuficiente):** si falta stock de cualquier insumo, no
  se registra nada y el sistema avisa.
- **Reglas:** RN01, RN03 y RNF-REL-01 (todo el carrito es atómico: o pasa la
  compra entera o no pasa nada).
- **RF propuesto:** El sistema permite registrar en una sola venta varios
  productos con sus cantidades (venta multi-ítem).

### CU-16. Actualizar Stock (Auto-descuento)
- **Actor:** Sistema (disparado por CU-15).
- **Descripción:** Dentro de la misma transacción de la venta, descuenta el stock
  de cada insumo según la receta y registra el movimiento en auditoría.
- **Precondición:** Se está confirmando una venta (CU-15).
- **Flujo básico:**
  1. El sistema consolida el consumo por insumo, sumando lo que aportan todos los
     productos del carrito.
  2. Por cada insumo bloquea la fila, verifica que haya stock suficiente,
     descuenta la cantidad y lo registra en `auditoria_inventario` (cantidad
     negativa, tipo "Venta").
  3. Si el stock de algún insumo no alcanza, revierte toda la venta.
- **Reglas:** RN01 (todo lo vendido descuenta stock), RNF-REL-01 (atomicidad).

### CU-18. Consultar Dashboard y Reportes
- **Actor:** Administrador.
- **Descripción:** Muestra KPIs en tiempo real y da acceso a los tres reportes.
- **Precondición:** El Administrador ha iniciado sesión.
- **Flujo básico:**
  1. El Administrador abre "Reportes".
  2. El sistema muestra los KPIs (ventas del día, insumos críticos, mermas,
     ingresos y total de insumos).
  3. El Administrador elige una pestaña (Ventas / Ajustes de inventario / Pedidos
     a proveedor), fija el rango de fechas y emite el reporte (CU-19/20/21).
- **Flujo alterno:** si no hay historial de transacciones, el sistema lo avisa y
  muestra los KPIs en cero.

### CU-19. Emitir Reporte de Ventas
- **Actor:** Administrador.
- **Descripción:** Lista las ventas de un periodo, cada una con el detalle de
  productos del pedido.
- **Precondición:** El Administrador está en "Reportes", pestaña "Ventas".
- **Flujo básico:**
  1. Elige el rango de fechas y pulsa "Emitir Reporte".
  2. El sistema muestra una fila por venta con su detalle de productos
     (cantidad, precio unitario, subtotal) y el total.
  3. (Opcional) pulsa "Exportar CSV" para descargar el reporte.
- **Reglas:** RN03; una fila por venta para no inflar totales al aplanar el
  detalle.

### CU-20. Emitir Reporte de Modificaciones de Inventario
- **Actor:** Administrador.
- **Descripción:** Lista los ajustes manuales de inventario de un periodo con su
  tipo y motivo.
- **Precondición:** El Administrador está en "Reportes", pestaña "Ajustes de
  inventario".
- **Flujo básico:**
  1. Elige el rango de fechas y pulsa "Emitir Reporte".
  2. El sistema muestra cada ajuste con su tipo de operación (merma, pérdida,
     ingreso), insumo, cantidad con signo y motivo.
  3. (Opcional) exporta a CSV.
- **Reglas:** excluye los movimientos de tipo "Venta" (esos van en el CU-19).

### CU-21. Emitir Reporte de Proveedores
- **Actor:** Administrador.
- **Descripción:** Lista los pedidos a proveedor de un periodo con su detalle.
- **Precondición:** El Administrador está en "Reportes", pestaña "Pedidos a
  proveedor".
- **Flujo básico:**
  1. Elige el rango de fechas y pulsa "Emitir Reporte".
  2. El sistema muestra una fila por pedido con proveedor, teléfono, estado y los
     insumos solicitados.
  3. (Opcional) exporta a CSV.
- **Reglas:** RN03.

---

## 3. Pendientes / a verificar con el equipo

- **CU-17. Generar Alerta de Stock Mínimo:** hoy solo se refleja como el KPI
  "insumos críticos" del dashboard y la lista de críticos en Pedidos. No hay una
  alerta dedicada; conviene decidir si eso cubre el CU o falta trabajo.
- **CU-09. Editar Receta:** en la práctica se cubre con CU-10/11/12 (editar,
  agregar y quitar insumos de la receta). No existe un "editar receta" aparte.

---

## 4. Nota de base de datos / arquitectura

- **No se agregaron tablas.** Las 12 tablas del esquema siguen igual.
- **Migración 008** — `registrar_venta_multiple`: función transaccional para la
  venta multi-ítem con descuento atómico de stock (CU-15/CU-16).
- **Migración 009** — `recetas_update_admin`: política RLS de UPDATE sobre
  `recetas` para poder editar cantidades respetando el aislamiento RN03
  (CU-12).
- **CRUD de productos (CU-22..25):** no necesitó migración; las políticas RLS de
  INSERT/UPDATE/DELETE sobre `productos` para el Administrador ya existían desde
  la migración 004, y el borrado en cascada de la receta ya estaba en el esquema.
- **Refactor interno:** `insumos.py`, `inventario.py` y `recetas.py` pasan a usar
  el cliente por request `get_supabase_usuario()` (token de la sesión) en vez del
  cliente singleton, para que RLS funcione de forma fiable ante reinicios del
  servidor y usuarios concurrentes.
