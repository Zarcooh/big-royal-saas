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
- **Nuevo:** buscador por nombre en el catálogo.
- **RF propuesto:** El sistema permite filtrar el catálogo de insumos por nombre
  (búsqueda parcial, sin distinguir mayúsculas).

### CU-06. Listar Recetas
- **Redacción actualizada:** ahora se presenta como el catálogo de productos
  (CU-22) desde el cual, por cada fila, se gestiona la receta del producto.

### CU-08. Eliminar Receta
- **Implementado:** desde "Gestionar receta", botón "Eliminar receta completa".
  Borra todas las líneas; el producto sigue existiendo (queda vendible sin
  descuento automático de stock, caso "producto sin receta" del CU-15).

### CU-10 / CU-11 / CU-12. Agregar / Eliminar / Editar Insumo de Receta
- **Implementados** en la pantalla "Gestionar receta":
  - Agregar insumo con su cantidad de consumo (valida duplicados, RF-INV-10).
  - Eliminar una línea de la receta.
  - Editar la cantidad de consumo de una línea.
- **Requirió cambio en BD:** la política RLS de UPDATE sobre `recetas` no existía;
  sin ella el editar cantidad fallaba en silencio. Se agregó
  `recetas_update_admin` (**migración 009**).

### CU-15. Registrar Venta
- **Redacción actualizada:** el Cajero arma un pedido con **uno o varios
  productos** (carrito en sesión), ajusta cantidades y lo confirma en un solo
  comprobante.
- **Atomicidad:** toda la venta corre en la RPC `registrar_venta_multiple`
  (**migración 008**): consolida el consumo por insumo y descuenta stock; si
  falta stock de cualquier ítem, no se registra nada (RNF-REL-01). Mantiene el
  aviso de "producto sin receta".
- **RF propuesto:** El sistema permite registrar en una sola venta varios
  productos con sus cantidades (venta multi-ítem).

### CU-16. Actualizar Stock (Auto-descuento)
- **Implementado** dentro de la misma RPC de venta: descuenta el stock de cada
  insumo según la receta y deja el registro en `auditoria_inventario`.

### CU-18. Consultar Dashboard y Reportes
- **Redacción actualizada:** KPIs en tiempo real (ventas del día, insumos
  críticos, mermas, ingresos, total de insumos) y acceso a los tres reportes.

### CU-19. Emitir Reporte de Ventas
- **Implementado** como pestaña: cada venta con el **detalle de productos** del
  pedido; filtro de fechas y exportación CSV.

### CU-20. Emitir Reporte de Modificaciones de Inventario
- **Implementado** como pestaña: ajustes manuales con **tipo de operación**
  (merma, pérdida, ingreso) y **motivo**, excluyendo los movimientos de venta.

### CU-21. Emitir Reporte de Proveedores
- **Implementado** como pestaña: pedidos a proveedor con proveedor, estado e
  insumos solicitados; filtro de fechas y CSV.

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
