# Cambios para el informe final — Big Royal SaaS

> Texto listo para pegar en el informe. Por cada CU afectado: la **redacción
> actualizada** (reemplaza a la anterior) y los **requisitos nuevos propuestos**
> (la numeración final la defines tú según tu esquema; por eso van como `RF-INV-XX`).
>
> Importante: **no se agregaron tablas nuevas** a la base de datos. Los cambios se
> apoyan en el esquema existente (12 tablas) e incorporan una función RPC y una
> política RLS. **No se agregaron requisitos no funcionales nuevos**; los
> existentes (RNF-REL-01, RN01, RN02, RN03) se respetaron y en un caso se
> ampliaron de alcance.

---

## CU-02 — Gestionar Catálogo de Insumos

**Redacción actualizada:**

> El Administrador puede crear, editar, eliminar y **buscar** insumos del
> restaurante. El buscador filtra el catálogo por nombre.

**Requisito nuevo propuesto:**

- **RF-INV-XX:** El sistema permite filtrar el catálogo de insumos por nombre
  (búsqueda parcial, sin distinguir mayúsculas).

---

## CU-03 — Gestionar Recetas

**Redacción actualizada:**

> El módulo presenta un **catálogo de productos** (al estilo del de insumos): el
> Administrador puede **crear, editar y eliminar productos** (nombre y precio) y,
> por cada uno, **gestionar su receta**: ver los insumos, **agregar** uno,
> **modificar la cantidad de consumo** de uno ya incluido, **eliminar un insumo**
> de la receta y **eliminar la receta completa**. Al eliminar solo la receta, el
> producto no se borra: queda vendible pero sin descuento automático de stock. Un
> producto **no puede eliminarse si ya tiene ventas registradas** (para no romper
> el historial que usan los reportes del CU-07); al borrar un producto sin ventas,
> su receta se elimina en cascada.

**Requisitos nuevos propuestos:**

- **RF-INV-XX:** El sistema permite crear un producto (nombre y precio de venta).
- **RF-INV-XX:** El sistema permite editar el nombre y el precio de un producto.
  El cambio de precio no altera el historial: cada venta guarda el precio con el
  que se vendió.
- **RF-INV-XX:** El sistema permite eliminar un producto y, en cascada, su receta,
  siempre que el producto no tenga ventas registradas.
- **RF-INV-XX:** El sistema permite filtrar el catálogo de productos por nombre.
- **RF-INV-XX:** El sistema permite modificar la cantidad de consumo de un insumo
  dentro de una receta.
- **RF-INV-XX:** El sistema permite eliminar un insumo individual de una receta.
- **RF-INV-XX:** El sistema permite eliminar todas las líneas de la receta de un
  producto sin eliminar el producto.

---

## CU-06 — Registrar Venta

**Redacción actualizada:**

> El Cajero arma un pedido agregando **uno o varios productos** a un detalle de
> venta (carrito), ajusta cantidades y confirma la compra en un solo comprobante.
> Al confirmar, el sistema descuenta automáticamente el stock de los insumos según
> la receta de cada producto. La operación es **atómica**: si falta stock de
> cualquier insumo del pedido, no se registra ninguna parte de la venta.

**Requisito nuevo propuesto:**

- **RF-INV-XX:** El sistema permite registrar en una sola venta varios productos
  con sus cantidades (venta multi-ítem), consolidando el consumo por insumo antes
  de descontar stock.

> Nota: no es un RNF nuevo. La atomicidad ya la cubría **RNF-REL-01**; aquí solo se
> extiende su alcance del producto individual al pedido completo.

---

## CU-07 — Consultar Dashboard y Reportes

**Redacción actualizada:**

> El Administrador consulta KPIs en tiempo real y emite tres reportes con filtro
> por fechas y exportación a CSV: **(1) Ventas**, cada venta con el detalle de
> productos del pedido; **(2) Ajustes de inventario**, con tipo de operación
> (merma, pérdida, ingreso) y motivo; **(3) Pedidos a proveedor**, con proveedor,
> estado e insumos solicitados.

**Requisitos nuevos propuestos:**

- **RF-INV-XX:** El sistema emite un reporte de ajustes manuales de inventario
  mostrando tipo de operación y motivo, excluyendo los movimientos generados por
  ventas.
- **RF-INV-XX:** El sistema emite un reporte de pedidos a proveedor con su detalle
  de insumos.
- **RF-INV-XX:** El reporte de ventas muestra el detalle de productos de cada venta
  (soporte a la venta multi-ítem del CU-06).

---

## Nota para la sección de base de datos / arquitectura

> No se agregaron tablas nuevas. Los cambios se apoyan en el esquema existente e
> incorporan: una función transaccional `registrar_venta_multiple` (venta
> multi-ítem con descuento atómico de stock — migración 008) y una política RLS de
> UPDATE sobre `recetas` que habilita la edición de cantidades respetando el
> aislamiento por restaurante RN03 (migración 009).
>
> El CRUD de productos (CU-03) no necesitó cambios en la base: las políticas RLS
> de INSERT, UPDATE y DELETE sobre `productos` para el rol Administrador ya
> existían desde la migración 004. El borrado de la receta al eliminar un producto
> se apoya en el `ON DELETE CASCADE` ya definido en `recetas.producto_id`.
