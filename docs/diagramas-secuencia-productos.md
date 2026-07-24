# Diagramas de secuencia — Módulo Productos

Diagramas de secuencia de los casos de uso del módulo de Productos y de la
gestión de recetas, basados en la implementación real (`app/routes/productos.py`).
Se usa la convención boundary-control-entity de los demás diagramas del proyecto:

- **`i_`** interfaz (boundary): la vista con la que interactúa el usuario.
- **`c_`** control: el blueprint/controlador de productos.
- **`e_`** entidad: las tablas de la base (`productos`, `recetas`, `insumos`,
  `ventas`/`detalle_ventas`).

> Estos diagramas se renderizan automáticamente en GitHub. Para el informe puedes
> exportarlos a imagen desde <https://mermaid.live> (pega el bloque `mermaid`).

---

## CU-22 — Listar Productos

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iP as i_principal
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iP: click en módulo "Productos"
    iP->>iR: mostrarCatalogo()
    iR->>cR: listar(q?)
    cR->>eProd: obtenerProductos(restaurante_id, q)
    eProd-->>cR: productos
    cR->>eRec: contarInsumosPorProducto(producto_ids)
    eRec-->>cR: conteo por producto
    cR-->>iR: catálogo (producto, precio, estado de receta)
    iR-->>Admin: muestra catálogo de productos

    alt No hay productos
        cR-->>iR: lista vacía
        iR-->>Admin: "No hay productos registrados"
    end
```

---

## CU-23 — Agregar Producto

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto

    Admin->>iR: click "+ Nuevo Producto"
    iR->>cR: crear() [GET]
    cR-->>iR: formulario (nombre, precio)
    iR-->>Admin: muestra el formulario
    Admin->>iR: ingresa nombre y precio, click "Guardar"
    iR->>cR: crear(nombre, precio) [POST]
    alt Nombre vacío o precio negativo
        cR-->>iR: error de validación
        iR-->>Admin: muestra el error (no se crea)
    else Datos válidos
        cR->>eProd: insertarProducto(restaurante_id, nombre, precio)
        eProd-->>cR: nuevo producto (id)
        cR-->>iR: redirigir a "Gestionar receta" + éxito
        iR-->>Admin: "Producto creado"
    end
```

---

## CU-24 — Editar Producto

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto

    Admin->>iR: click "Editar" (producto_id)
    iR->>cR: editar(producto_id) [GET]
    cR->>eProd: obtenerProducto(producto_id, restaurante_id)
    eProd-->>cR: producto
    cR-->>iR: formulario precargado
    iR-->>Admin: muestra nombre y precio actuales
    Admin->>iR: cambia nombre/precio, click "Guardar"
    iR->>cR: editar(producto_id, nombre, precio) [POST]
    alt Nombre vacío o precio negativo
        cR-->>iR: error de validación
        iR-->>Admin: muestra el error (no se guarda)
    else Datos válidos
        cR->>eProd: actualizarProducto(producto_id, nombre, precio)
        eProd-->>cR: actualizado
        cR-->>iR: redirigir al catálogo + éxito
        iR-->>Admin: "Producto actualizado"
    end
```

---

## CU-25 — Eliminar Producto

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eVen as e_venta
    participant eRec as e_receta

    Admin->>iR: click "Eliminar"
    iR->>Admin: solicita confirmación
    Admin->>iR: confirma
    iR->>cR: eliminar(producto_id) [POST]
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eVen: verificarVentas(producto_id)
    alt El producto tiene ventas
        eVen-->>cR: tiene ventas
        cR-->>iR: "No se puede eliminar: tiene ventas"
        iR-->>Admin: producto NO eliminado
    else Sin ventas
        eVen-->>cR: sin ventas
        cR->>eProd: eliminarProducto(producto_id)
        eProd->>eRec: ON DELETE CASCADE (borra la receta)
        cR-->>iR: redirigir + "producto eliminado"
        iR-->>Admin: producto eliminado
    end
```

---

## CU-08 — Eliminar Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iR: click "Eliminar receta completa"
    iR->>Admin: solicita confirmación
    Admin->>iR: confirma
    iR->>cR: eliminarReceta(producto_id)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eRec: eliminarTodasLasLineas(producto_id)
    eRec-->>cR: n líneas eliminadas
    cR-->>iR: redirigir + "receta eliminada"
    iR-->>Admin: producto queda sin receta (vendible sin descuento)
```

---

## CU-10 — Agregar Insumo a Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eIns as e_insumo
    participant eRec as e_receta

    Note over iR: El desplegable solo ofrece insumos aún NO incluidos
    Admin->>iR: seleccionar insumo + cantidad, click "Agregar"
    iR->>cR: agregarInsumo(producto_id, insumo_id, cantidad)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eIns: validarInsumoDelTenant(insumo_id, restaurante_id)
    eIns-->>cR: insumo válido
    alt Cantidad <= 0
        cR-->>iR: error de validación
    else Cantidad válida
        cR->>eRec: existeLinea(producto_id, insumo_id)?
        alt Ya existe (salvaguarda)
            eRec-->>cR: existe
            cR-->>iR: aviso "ya forma parte de la receta"
        else No existe
            eRec-->>cR: no existe
            cR->>eRec: insertarLinea(producto_id, insumo_id, cantidad)
            eRec-->>cR: línea creada
            cR-->>iR: redirigir + "insumo agregado"
        end
    end
    iR-->>Admin: receta actualizada
```

---

## CU-11 — Eliminar Insumo de Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iR: click "Eliminar" en la fila del insumo
    iR->>Admin: solicita confirmación
    Admin->>iR: confirma
    iR->>cR: eliminarInsumo(producto_id, linea_id)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eRec: eliminarLinea(linea_id, producto_id)
    eRec-->>cR: línea eliminada
    cR-->>iR: redirigir + "insumo eliminado de la receta"
    iR-->>Admin: receta actualizada
```

---

## CU-12 — Editar Insumo de Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Productos
    participant cR as c_Productos
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iR: cambiar cantidad, click "Guardar"
    iR->>cR: editarInsumo(producto_id, linea_id, cantidad)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    alt Cantidad <= 0
        cR-->>iR: error "cantidad debe ser mayor que cero"
    else Cantidad válida
        cR->>eRec: actualizarCantidad(linea_id, producto_id, cantidad)
        eRec-->>cR: cantidad actualizada
        cR-->>iR: redirigir + "cantidad actualizada"
    end
    iR-->>Admin: receta actualizada
```
