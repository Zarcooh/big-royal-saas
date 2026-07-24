# Cambios para el informe final — Big Royal SaaS

Casos de uso implementados/actualizados en la rama
`feature/mejoras-carrito-recetas-reportes` (PR #5 → `develop`), redactados con la
plantilla de casos de uso del equipo.

**Puntos clave:**
- **No se agregaron tablas** a la base de datos (siguen siendo 12).
- Se agregaron 1 función RPC y 1 política RLS (migraciones 008 y 009).
- **No se agregaron requisitos no funcionales nuevos**; los existentes
  (RNF-REL-01 atomicidad, RN01, RN02, RN03) se respetaron.
- **Nuevos:** CU-22 a CU-25 (gestión de Productos). El resto son CU existentes
  cuya funcionalidad se implementó/amplió.

---

## Resumen rápido

| CU | Nombre | Estado |
| --- | --- | --- |
| CU-02 | Listar Insumos | Ampliado (buscador) |
| CU-06 | Listar Recetas | **Misma interfaz que CU-22** (Listar Productos) |
| CU-07 | Agregar Recetas | **Reemplazado por CU-10** (Agregar Insumo a Receta) |
| CU-08 | Eliminar Receta | Implementado |
| CU-09 | Editar Receta | **Reemplazado por CU-12** (Editar Insumo de Receta) |
| CU-10 | Agregar Insumo a Receta | Implementado |
| CU-11 | Eliminar Insumo de Receta | Implementado |
| CU-12 | Editar Insumo de Receta | Implementado (requirió migración 009) |
| CU-15 | Registrar Venta | Ampliado (carrito multi-ítem) |
| CU-16 | Actualizar Stock (Auto-descuento) | Implementado (migración 008) |
| CU-18 | Consultar Dashboard y Reportes | Implementado |
| CU-19 | Emitir Reporte de Ventas | Implementado |
| CU-20 | Emitir Reporte de Modificaciones de Inventario | Implementado |
| CU-21 | Emitir Reporte de Proveedores | Implementado |
| **CU-22** | **Listar Productos** | **Nuevo** |
| **CU-23** | **Agregar Producto** | **Nuevo** |
| **CU-24** | **Editar Producto** | **Nuevo** |
| **CU-25** | **Eliminar Producto** | **Nuevo** |

---

## Casos de uso

### CU-02 — Listar Insumos

| Caso de uso | Listar Insumos |
| --- | --- |
| **ID** | CU-02 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador visualizar el catálogo de insumos del restaurante con su stock actual y mínimo, con búsqueda por nombre. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador accede al módulo "Insumos". | 2. El sistema consulta y lista los insumos del restaurante con nombre, unidad, stock actual y stock mínimo, ordenados alfabéticamente, resaltando los que están en o bajo el mínimo. |
| 3. El Administrador busca o filtra insumos por nombre. | 4. El sistema filtra la lista según el criterio ingresado. |

**Flujos alternos**

- **1.1.** Si el usuario no posee el rol de Administrador, el sistema deniega el acceso al módulo.
- **2.1.** Si no existen insumos registrados, muestra "No hay insumos registrados".
- **4.1.** Si ningún insumo coincide con la búsqueda, muestra un mensaje y ofrece ver todos.

**Condiciones**

- **Pre-condiciones:** el usuario ha iniciado sesión con rol de Administrador.
- **Post-condiciones:** el listado (filtrado o completo) queda desplegado en pantalla.

---

### CU-06 — Listar Recetas → CU-22 (Listar Productos)

> **No es un caso de uso aparte.** "Listar Recetas" abre exactamente la misma
> interfaz que **CU-22 (Listar Productos)**: el catálogo de productos donde cada
> fila muestra el estado de su receta. Se documenta bajo CU-22 para no duplicar.
> Ver la receta de un producto se hace con "Gestionar receta" (que abre CU-08 /
> CU-10 / CU-11 / CU-12).

---

### CU-07 — Agregar Recetas → CU-10 (Agregar Insumo a Receta)

> **No es un caso de uso aparte.** En la app no hay un botón de "crear/agregar
> receta": una receta se arma **agregando insumos** al producto. Por tanto
> "Agregar Recetas" se cubre con **CU-10 (Agregar Insumo a Receta)** — la primera
> vez que se agrega un insumo, se crea la receta. La pantalla "Gestionar receta"
> es solo el contenedor de las operaciones CU-08 / CU-10 / CU-11 / CU-12.

---

### CU-08 — Eliminar Receta

| Caso de uso | Eliminar Receta |
| --- | --- |
| **ID** | CU-08 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador eliminar todas las líneas de la receta de un producto, sin eliminar el producto. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. En "Gestionar receta", el Administrador pulsa "Eliminar receta completa" (el botón **solo aparece si el producto tiene receta**). | 2. El sistema pide confirmación. |
| 3. El Administrador confirma. | 4. El sistema elimina todas las líneas de la receta y muestra un mensaje de éxito. |

**Flujos alternos**

- **3.1.** Si el Administrador cancela, no se realiza ningún cambio.
- **4.1.** *(Salvaguarda)* Si el producto no tuviera receta, el sistema informa que no había receta que eliminar; en la práctica el botón solo se muestra cuando hay receta, así que este caso no se alcanza desde la interfaz.

**Condiciones**

- **Pre-condiciones:** sesión con rol Administrador; el producto pertenece al restaurante.
- **Post-condiciones:** el producto queda sin receta (vendible sin descuento automático de stock).

---

### CU-10 — Agregar Insumo a Receta

| Caso de uso | Agregar Insumo a Receta |
| --- | --- |
| **ID** | CU-10 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador agregar un insumo a la receta de un producto con su cantidad de consumo por unidad vendida. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. En "Gestionar receta", el Administrador selecciona un insumo del desplegable —que **solo muestra los insumos aún NO incluidos** en la receta—, ingresa la cantidad de consumo y pulsa "Agregar". | 2. El sistema valida los datos, agrega la línea a la receta y actualiza la vista. |

**Flujos alternos**

- **1.1.** Si todos los insumos del catálogo ya están en la receta, el desplegable queda sin opciones y el sistema informa que "no quedan insumos disponibles".
- **2.1.** Si la cantidad es menor o igual a cero, o el insumo no es válido o no pertenece al restaurante, el sistema muestra un error y no agrega la línea.
- **2.2.** *(Salvaguarda)* Como el desplegable ya excluye los insumos repetidos, no se puede elegir uno duplicado desde la interfaz; si aun así llegara uno, el servidor lo rechaza (RF-INV-10 / restricción UNIQUE).

**Condiciones**

- **Pre-condiciones:** sesión Administrador; el producto pertenece al restaurante y queda al menos un insumo no incluido.
- **Post-condiciones:** el insumo queda en la receta con su cantidad de consumo.

---

### CU-11 — Eliminar Insumo de Receta

| Caso de uso | Eliminar Insumo de Receta |
| --- | --- |
| **ID** | CU-11 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador quitar un insumo de la receta de un producto. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador pulsa "Eliminar" en la fila del insumo. | 2. El sistema solicita confirmación. |
| 3. El Administrador confirma. | 4. El sistema quita la línea de la receta y actualiza la vista. |

**Flujos alternos**

- **3.1.** Si el Administrador cancela (diálogo de confirmación), no se realiza ningún cambio.
- **4.1.** *(Salvaguarda)* Si la línea no perteneciera a la receta del producto, el sistema informa la inconsistencia; en el flujo normal el botón "Eliminar" está en la propia fila del insumo, así que siempre corresponde.

**Condiciones**

- **Pre-condiciones:** sesión Administrador; el insumo forma parte de la receta.
- **Post-condiciones:** el insumo ya no está en la receta.

---

### CU-12 — Editar Insumo de Receta

| Caso de uso | Editar Insumo de Receta |
| --- | --- |
| **ID** | CU-12 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador modificar la cantidad de consumo de un insumo ya presente en la receta. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador cambia la cantidad en la fila del insumo y pulsa "Guardar". | 2. El sistema valida y actualiza la cantidad de consumo. |

**Flujos alternos**

- **2.1.** Si la cantidad es menor o igual a cero (o vacía), el sistema muestra un error y no guarda. *(El input ya exige `min=0.001`, pero el servidor lo revalida.)*
- **2.2.** *(Salvaguarda)* Si la línea no perteneciera al producto, el sistema informa la inconsistencia; en el flujo normal el campo de cantidad está en la propia fila del insumo, así que siempre corresponde.

**Condiciones**

- **Pre-condiciones:** sesión Administrador; el insumo forma parte de la receta.
- **Post-condiciones:** la cantidad de consumo queda actualizada.

---

### CU-15 — Registrar Venta

| Caso de uso | Registrar Venta |
| --- | --- |
| **ID** | CU-15 |
| **Actor(es)** | Cajero |
| **Objetivo** | Permitir al Cajero registrar una venta de uno o varios productos en un solo comprobante, descontando el stock automáticamente. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Cajero accede a "Registrar Venta". | 2. El sistema muestra el catálogo con la receta de cada producto y el detalle del pedido (vacío). |
| 3. El Cajero indica la cantidad y pulsa "Agregar" por cada producto. | 4. El sistema añade cada producto al detalle del pedido y actualiza el total. |
| 5. El Cajero ajusta cantidades o quita ítems del pedido (opcional). | 6. El sistema recalcula el detalle y el total. |
| 7. El Cajero pulsa "Confirmar compra". | 8. El sistema registra la venta, descuenta el stock (CU-16) de forma atómica y muestra el comprobante con el detalle y el stock actualizado. |

**Flujos alternos**

- **7.1.** Si el pedido está vacío, el sistema solicita agregar al menos un producto.
- **8.1.** Si algún producto no tiene receta configurada, el sistema **rechaza toda la venta** y avisa que ese producto no se puede vender hasta definir su receta (no hay opción de continuar). Un producto solo es vendible si tiene receta, para que toda venta descuente stock.
- **8.2.** Si falta stock de algún insumo, no se registra nada y el sistema avisa "stock insuficiente".

**Condiciones**

- **Pre-condiciones:** sesión con rol Cajero (o Administrador); existen productos **con receta** registrados.
- **Post-condiciones:** la venta y su detalle quedan registrados y el stock actualizado; ante cualquier error, no cambia nada (operación atómica, RNF-REL-01).

---

### CU-16 — Actualizar Stock (Auto-descuento)

| Caso de uso | Actualizar Stock (Auto-descuento) |
| --- | --- |
| **ID** | CU-16 |
| **Actor(es)** | Sistema (disparado por CU-15) |
| **Objetivo** | Descontar el stock de los insumos según la receta de los productos vendidos y registrar el movimiento en auditoría, de forma atómica. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. (Disparado al confirmar una venta en CU-15.) | 2. El sistema consolida el consumo por insumo, sumando el aporte de todos los productos del pedido. |
| — | 3. Por cada insumo, el sistema bloquea la fila, verifica que haya stock suficiente, descuenta la cantidad y registra el movimiento en auditoría (cantidad negativa, tipo "Venta"). |

**Flujos alternos**

- **3.1.** Si el stock de algún insumo no alcanza, el sistema revierte toda la venta (no queda descuento parcial).

**Condiciones**

- **Pre-condiciones:** se está confirmando una venta válida (CU-15).
- **Post-condiciones:** el stock de cada insumo queda descontado y auditado; o, ante error, la venta se revierte por completo.

---

### CU-18 — Consultar Dashboard y Reportes

| Caso de uso | Consultar Dashboard y Reportes |
| --- | --- |
| **ID** | CU-18 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador consultar indicadores (KPIs) en tiempo real y acceder a los reportes. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador accede a "Reportes". | 2. El sistema muestra los KPIs: ventas del día, insumos críticos, mermas, ingresos y total de insumos. |
| 3. El Administrador selecciona una pestaña (Ventas / Ajustes de inventario / Pedidos a proveedor) y fija el rango de fechas. | 4. El sistema conserva la pestaña y el rango, y muestra el formulario del reporte. |
| 5. El Administrador pulsa "Emitir Reporte". | 6. El sistema muestra el reporte correspondiente (CU-19, CU-20 o CU-21). |

**Flujos alternos**

- **1.1.** Si el usuario no es Administrador, el sistema deniega el acceso.
- **2.1.** Si no hay historial de transacciones, el sistema lo avisa y muestra los KPIs en cero.

**Condiciones**

- **Pre-condiciones:** sesión con rol Administrador.
- **Post-condiciones:** los KPIs y, si se emitió, el reporte quedan desplegados.

---

### CU-19 — Emitir Reporte de Ventas

| Caso de uso | Emitir Reporte de Ventas |
| --- | --- |
| **ID** | CU-19 |
| **Actor(es)** | Administrador |
| **Objetivo** | Emitir un reporte de las ventas de un periodo con el detalle de productos de cada venta. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. En la pestaña "Ventas", el Administrador elige el rango de fechas y pulsa "Emitir Reporte". | 2. El sistema lista una fila por venta con su detalle (producto, cantidad, precio unitario, subtotal) y el total. |
| 3. El Administrador pulsa "Exportar CSV" (opcional). | 4. El sistema descarga el reporte en formato CSV. |

**Flujos alternos**

- **1.1.** Si la fecha "desde" es posterior a "hasta", el sistema avisa y no emite.
- **2.1.** Si no hay ventas en el rango, el sistema muestra "No se hallaron registros".

**Condiciones**

- **Pre-condiciones:** sesión Administrador.
- **Post-condiciones:** el reporte de ventas queda desplegado (y/o descargado en CSV).

---

### CU-20 — Emitir Reporte de Modificaciones de Inventario

| Caso de uso | Emitir Reporte de Modificaciones de Inventario |
| --- | --- |
| **ID** | CU-20 |
| **Actor(es)** | Administrador |
| **Objetivo** | Emitir un reporte de los ajustes manuales de inventario de un periodo con su tipo de operación y motivo. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. En la pestaña "Ajustes de inventario", el Administrador elige el rango y pulsa "Emitir Reporte". | 2. El sistema lista cada ajuste con su tipo (merma, pérdida, ingreso), insumo, cantidad con signo y motivo. |
| 3. El Administrador exporta a CSV (opcional). | 4. El sistema descarga el reporte en CSV. |

**Flujos alternos**

- **2.1.** Si no hay ajustes en el rango, el sistema muestra "No se hallaron registros".

**Condiciones**

- **Pre-condiciones:** sesión Administrador.
- **Post-condiciones:** el reporte de ajustes queda desplegado; excluye los movimientos de tipo "Venta".

---

### CU-21 — Emitir Reporte de Proveedores

| Caso de uso | Emitir Reporte de Proveedores |
| --- | --- |
| **ID** | CU-21 |
| **Actor(es)** | Administrador |
| **Objetivo** | Emitir un reporte de los pedidos a proveedor de un periodo con su detalle. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. En la pestaña "Pedidos a proveedor", el Administrador elige el rango y pulsa "Emitir Reporte". | 2. El sistema lista una fila por pedido con proveedor, teléfono, estado e insumos solicitados. |
| 3. El Administrador exporta a CSV (opcional). | 4. El sistema descarga el reporte en CSV. |

**Flujos alternos**

- **2.1.** Si no hay pedidos en el rango, el sistema muestra "No se hallaron registros".

**Condiciones**

- **Pre-condiciones:** sesión Administrador.
- **Post-condiciones:** el reporte de pedidos queda desplegado.

---

### CU-22 — Listar Productos

| Caso de uso | Listar Productos |
| --- | --- |
| **ID** | CU-22 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador visualizar el catálogo de productos del restaurante con su precio y el estado de su receta, con búsqueda por nombre. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador accede al módulo "Recetas". | 2. El sistema lista los productos con nombre, precio y estado de receta (n.º de insumos o "sin receta"), ordenados alfabéticamente. |
| 3. El Administrador busca o filtra por nombre. | 4. El sistema filtra la lista según el criterio ingresado. |

**Flujos alternos**

- **1.1.** Si el usuario no es Administrador, el sistema deniega el acceso.
- **2.1.** Si no hay productos registrados, muestra "No hay productos registrados".
- **4.1.** Si ningún producto coincide con la búsqueda, muestra un mensaje y ofrece ver todos.

**Condiciones**

- **Pre-condiciones:** sesión con rol Administrador.
- **Post-condiciones:** el catálogo de productos queda desplegado.

---

### CU-23 — Agregar Producto

| Caso de uso | Agregar Producto |
| --- | --- |
| **ID** | CU-23 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador crear un producto con nombre y precio de venta. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador pulsa "+ Nuevo Producto". | 2. El sistema muestra el formulario de creación (nombre y precio). |
| 3. El Administrador ingresa nombre y precio y guarda. | 4. El sistema valida, crea el producto y redirige a "Gestionar receta" del nuevo producto. |

**Flujos alternos**

- **4.1.** Si el nombre está vacío o el precio es inválido o negativo, el sistema muestra un error y no crea el producto.

**Condiciones**

- **Pre-condiciones:** sesión con rol Administrador.
- **Post-condiciones:** el producto queda registrado en el restaurante.

---

### CU-24 — Editar Producto

| Caso de uso | Editar Producto |
| --- | --- |
| **ID** | CU-24 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador modificar el nombre y el precio de un producto. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador pulsa "Editar" en la fila del producto. | 2. El sistema muestra el formulario precargado con el nombre y el precio actuales. |
| 3. El Administrador cambia el nombre y/o el precio y guarda. | 4. El sistema valida y actualiza el producto. |

**Flujos alternos**

- **2.1.** Si el producto no existe o no pertenece al restaurante, el sistema informa y vuelve al catálogo.
- **4.1.** Si el nombre está vacío o el precio es inválido o negativo, el sistema muestra un error y no guarda.

**Condiciones**

- **Pre-condiciones:** sesión Administrador; el producto pertenece al restaurante.
- **Post-condiciones:** el nombre y/o el precio quedan actualizados. El cambio de precio no altera el precio ya registrado en ventas anteriores.

---

### CU-25 — Eliminar Producto

| Caso de uso | Eliminar Producto |
| --- | --- |
| **ID** | CU-25 |
| **Actor(es)** | Administrador |
| **Objetivo** | Permitir al Administrador eliminar un producto y, en cascada, su receta. |

**Flujo básico**

| Acción del Actor | Respuesta del Sistema |
| --- | --- |
| 1. El Administrador pulsa "Eliminar" en la fila del producto. | 2. El sistema solicita confirmación. |
| 3. El Administrador confirma. | 4. El sistema elimina el producto y su receta (en cascada) y muestra un mensaje de éxito. |

**Flujos alternos**

- **3.1.** Si el Administrador cancela, no se realiza ningún cambio.
- **4.1.** Si el producto tiene ventas registradas, el sistema rechaza el borrado y avisa (protege el historial que usan los reportes).

**Condiciones**

- **Pre-condiciones:** sesión Administrador; el producto pertenece al restaurante y no tiene ventas registradas.
- **Post-condiciones:** el producto y su receta quedan eliminados.

---

## Pendientes / a verificar con el equipo

- **Módulo renombrado a "Productos":** en la interfaz (navbar, panel y
  encabezado) el módulo se llama **Productos**, no "Recetas": la pantalla es el
  catálogo de productos y la receta es una función por producto ("Gestionar
  receta"). La ruta interna es **`/productos`** (blueprint `productos`,
  `app/routes/productos.py`, plantillas en `app/templates/productos/`). La
  **tabla de BD sigue llamándose `recetas`**.
- **CU-06, CU-07 y CU-09 dejan de ser CU propios** (decisión del equipo):
  - **CU-06 (Listar Recetas)** = misma interfaz que **CU-22 (Listar Productos)**.
  - **CU-07 (Agregar Recetas)** = **CU-10 (Agregar Insumo a Receta)** (no hay un
    "crear receta"; la receta se arma agregando insumos).
  - **CU-09 (Editar Receta)** = **CU-12 (Editar Insumo de Receta)**.
  - Quedan como CU reales del área: **CU-08** (Eliminar Receta), **CU-10**,
    **CU-11**, **CU-12**. Los números CU-06, CU-07 y CU-09 quedan libres para
    reasignar.
- **CU-17. Generar Alerta de Stock Mínimo:** hoy solo se refleja como el KPI
  "insumos críticos" del dashboard y la lista de críticos en Pedidos; no hay una
  alerta dedicada.

---

## Nota de base de datos / arquitectura

- **No se agregaron tablas.** Las 12 tablas del esquema siguen igual. En
  particular, `productos` (CU-22..25) ya existía desde la migración
  `001_initial_schema.sql`; solo se agregó la interfaz para gestionarla.
- **Migración 008** — `registrar_venta_multiple`: función transaccional para la
  venta multi-ítem con descuento atómico de stock (CU-15 / CU-16).
- **Migración 009** — `recetas_update_admin`: política RLS de UPDATE sobre
  `recetas` para poder editar cantidades respetando el aislamiento RN03 (CU-12).
- **Migración 010** — `registrar_venta_multiple` (nueva firma sin el parámetro
  de "confirmar sin receta"): la venta **exige** que todos los productos tengan
  receta; si alguno no la tiene, se rechaza el pedido completo. Así toda venta
  descuenta stock y no hay forma de vender algo que no lo controle (CU-15).
- **CRUD de productos (CU-22..25):** no necesitó migración; las políticas RLS de
  INSERT/UPDATE/DELETE sobre `productos` para el Administrador ya existían desde
  la migración 004, y el borrado en cascada de la receta ya estaba en el esquema.
- **Refactor interno:** `insumos.py`, `inventario.py` y `recetas.py` pasan a usar
  el cliente por request `get_supabase_usuario()` (token de la sesión) para que
  RLS funcione de forma fiable ante reinicios del servidor y usuarios concurrentes.
