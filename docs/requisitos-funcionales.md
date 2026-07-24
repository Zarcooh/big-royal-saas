# Requisitos funcionales — Big Royal SaaS

Lista consolidada de requisitos funcionales del sistema, **revisada contra la
implementación real** (código en `app/` y migraciones). Incluye:

- Los **22 RF existentes** (RF-INV-01 … RF-INV-22), con correcciones donde la
  redacción no coincidía con lo implementado.
- **8 RF nuevos** (RF-INV-23 … RF-INV-30) por las funciones agregadas: módulo de
  Productos, registrar venta (carrito), exigir receta, rechazar por stock, y la
  auditoría de ingreso.

> Los números 23–30 son una propuesta; renumérenlos si su esquema lo requiere.

---

## Resumen de la revisión

**Correcciones a RF existentes:**
- **RF-INV-01** — agregar que también permite **búsqueda por nombre**.
- **RF-INV-04** — se precisa: valida que el insumo **no esté usado en ninguna
  receta** (no un FK genérico).
- **RF-INV-16** — agregar que el ajuste indica **tipo (merma, pérdida, ingreso) y
  motivo**.
- **RF-INV-18** — ✅ **Implementado** (migración 011): tras el auto-descuento de
  una venta, si un insumo cruza a su mínimo se genera una alerta en el módulo
  **Alertas**, con contador en el navbar y aviso en el comprobante del Cajero.
- **RF-INV-20 / 21 / 22** — agregar **exportación a CSV**; y en ventas, el
  **detalle de productos por venta**.
- **RF-INV-05** — el alcance real del control de rol Administrador abarca insumos,
  **productos**, recetas, ajustes y pedidos (no solo insumos).

**RF nuevos que faltaban (RF-INV-23 … 30):** auditoría de ingreso; listar / crear
/ editar / eliminar **producto**; registrar **venta multi-ítem**; **exigir
receta** para vender; **rechazar por stock insuficiente**.

---

## Lista consolidada (por módulo)

### Autenticación y seguridad

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-15 | Autenticar al usuario mediante credenciales y token de sesión (JWT) según su rol. | Sistema | ✅ |
| **RF-INV-23** *(nuevo)* | Registrar en la auditoría de accesos el ingreso de cada usuario autenticado. | Sistema | ✅ |
| RF-INV-05 | Restringir a solo el rol Administrador la creación/edición/eliminación de insumos, **productos**, recetas, ajustes de inventario y pedidos. | Sistema | ✅ |
| RF-INV-06 | Aplicar aislamiento por restaurante (ningún tenant puede ver/modificar datos de otro). | Sistema | ✅ |

### Insumos

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-01 | Listar los insumos del restaurante (nombre, unidad, stock actual y mínimo) y **permitir búsqueda por nombre**. | Administrador / Sistema | ✅ *(corregido)* |
| RF-INV-02 | Crear insumo con nombre y unidad obligatorios; stock inicial y mínimo opcionales. | Administrador | ✅ |
| RF-INV-03 | Editar nombre, unidad, stock_actual y stock_minimo de un insumo del restaurante. | Administrador | ✅ |
| RF-INV-04 | Eliminar insumo, **validando que no esté usado en ninguna receta** (evita romper llaves foráneas). | Administrador | ✅ *(corregido)* |

### Productos *(módulo nuevo — CU-22 a CU-25)*

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| **RF-INV-24** *(nuevo)* | Listar los productos del restaurante (nombre, precio y estado de su receta) y permitir búsqueda por nombre. | Administrador / Sistema | ✅ |
| **RF-INV-25** *(nuevo)* | Crear un producto con nombre y precio de venta. | Administrador | ✅ |
| **RF-INV-26** *(nuevo)* | Editar el nombre y el precio de un producto, sin alterar el precio ya registrado en ventas anteriores. | Administrador | ✅ |
| **RF-INV-27** *(nuevo)* | Eliminar un producto (bloqueado si tiene ventas registradas); su receta se elimina en cascada. | Administrador | ✅ |

### Recetas (por producto)

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-07 | Ver la receta de un producto: lista de insumos con su cantidad y unidad. | Administrador | ✅ |
| RF-INV-11 | Listar las recetas configuradas de los productos (se muestra como el estado de receta en el catálogo de productos). | Administrador / Sistema | ✅ |
| RF-INV-08 | Agregar un insumo a una receta definiendo la cantidad de consumo por unidad vendida. | Administrador | ✅ |
| RF-INV-09 | Validar cross-tenant: el producto y el insumo deben pertenecer al mismo restaurante. | Sistema | ✅ |
| RF-INV-13 | Editar la cantidad de consumo de un insumo dentro de una receta. | Administrador | ✅ |
| RF-INV-14 | Eliminar un insumo de la receta de un producto. | Administrador | ✅ |
| RF-INV-12 | Eliminar por completo la receta de un producto (el producto no se elimina). | Administrador | ✅ |

### Ventas

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| **RF-INV-28** *(nuevo)* | Registrar una venta de uno o varios productos (carrito) en un solo comprobante, de forma atómica (todo o nada). | Cajero | ✅ |
| **RF-INV-29** *(nuevo)* | Exigir que el producto tenga receta configurada para poder venderlo (rechaza los productos sin receta). | Sistema | ✅ |
| **RF-INV-30** *(nuevo)* | Rechazar la venta si no hay stock suficiente de algún insumo, sin registrar nada. | Sistema | ✅ |
| RF-INV-10 | Auto-descontar el stock de los insumos mediante RPC tras confirmar la venta, con registro en auditoría. | Cajero / Sistema | ✅ |

### Inventario

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-16 | Ajustar manualmente el stock de un insumo indicando **tipo (merma, pérdida o ingreso) y motivo**, dejando registro en el log de auditoría. | Administrador | ✅ *(corregido)* |
| RF-INV-18 | Generar una alerta automática cuando, tras el auto-descuento de una venta, el stock de un insumo cruce a su nivel mínimo (visible en el módulo **Alertas**). | Sistema | ✅ *(migración 011 — CU-17)* |

### Proveedores

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-17 | Generar una orden de pedido al proveedor con los insumos que alcanzaron su nivel mínimo. | Administrador | ✅ |

### Reportes / Dashboard

| ID | Descripción | Actor | Estado |
| --- | --- | --- | --- |
| RF-INV-19 | Consolidar y mostrar en tiempo real los indicadores de stock en el Dashboard. | Sistema | ✅ |
| RF-INV-20 | Emitir el reporte de ventas filtrado por rango de fechas, **con el detalle de productos por venta y exportación a CSV**. | Administrador | ✅ *(corregido)* |
| RF-INV-21 | Emitir el reporte de modificaciones de inventario (ajustes, mermas y auto-descuentos) filtrado por fechas, **con exportación a CSV**. | Administrador | ✅ *(corregido)* |
| RF-INV-22 | Emitir el reporte de órdenes de pedido por proveedor filtrado por fechas, **con exportación a CSV**. | Administrador | ✅ *(corregido)* |

---

## RF-INV-18 — Alerta de stock mínimo (implementado, CU-17)

La RPC `registrar_venta_multiple` (migración 011) detecta, tras descontar cada
insumo, si su stock **cruzó** de estar por encima a estar en o por debajo del
mínimo; en ese caso inserta una fila en la tabla `alertas_stock`. Las alertas se
muestran en tres lugares:

- **Módulo Alertas** (`/alertas`, solo Administrador): lista de alertas activas
  (o todas), con opción de marcarlas como **atendidas**.
- **Contador** junto al enlace "Alertas" del navbar (número de alertas activas).
- **Aviso en el comprobante** de la venta que las disparó: el Cajero ve qué
  insumos quedaron en o bajo su mínimo.

Solo se genera en el **cruce** (no en cada venta mientras siga crítico), para no
duplicar alertas del mismo insumo.
