# Diagramas de secuencia — Módulo Recetas

Diagramas de secuencia de los casos de uso del módulo de Recetas, basados en la
implementación real (`app/routes/recetas.py`). Se usa la convención
boundary-control-entity de los demás diagramas del proyecto:

- **`i_`** interfaz (boundary): la vista con la que interactúa el usuario.
- **`c_`** control: el blueprint/controlador de recetas.
- **`e_`** entidad: las tablas de la base (`productos`, `recetas`, `insumos`).

> Estos diagramas se renderizan automáticamente en GitHub. Para el informe puedes
> exportarlos a imagen desde <https://mermaid.live> (pega el bloque `mermaid`).

---

## CU-06 — Listar Recetas (= CU-22 Listar Productos)

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iP as i_principal
    participant iR as i_Recetas
    participant cR as c_Recetas
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iP: click en módulo "Recetas"
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

## CU-07 — Gestionar Receta (contenedor de CU-08/10/11/12)

Carga de la pantalla única desde la que se realizan las operaciones sobre la
receta. No es un CU aparte: "Agregar receta" se cubre con CU-10 y "Editar
receta" con CU-12; aquí solo se muestra la carga de la pantalla.

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Recetas
    participant cR as c_Recetas
    participant eProd as e_producto
    participant eRec as e_receta
    participant eIns as e_insumo

    Admin->>iR: click "Gestionar receta" (producto_id)
    iR->>cR: gestionar(producto_id)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    alt Producto no existe o de otro restaurante
        eProd-->>cR: no encontrado
        cR-->>iR: redirigir a catálogo + aviso
    else Producto válido
        eProd-->>cR: producto
        cR->>eRec: obtenerReceta(producto_id)
        eRec-->>cR: líneas (insumo + cantidad)
        cR->>eIns: listarInsumosDisponibles(restaurante_id)
        eIns-->>cR: insumos no incluidos aún
        cR-->>iR: receta + insumos disponibles
        iR-->>Admin: muestra pantalla "Gestionar receta"
    end
```

---

## CU-10 — Agregar Insumo a Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Recetas
    participant cR as c_Recetas
    participant eProd as e_producto
    participant eIns as e_insumo
    participant eRec as e_receta

    Admin->>iR: seleccionar insumo + cantidad, click "Agregar"
    iR->>cR: agregarInsumo(producto_id, insumo_id, cantidad)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eIns: validarInsumoDelTenant(insumo_id, restaurante_id)
    eIns-->>cR: insumo válido
    cR->>eRec: existeLinea(producto_id, insumo_id)?
    alt Insumo ya está en la receta
        eRec-->>cR: existe
        cR-->>iR: aviso "ya forma parte de la receta"
    else Cantidad <= 0 o insumo inválido
        cR-->>iR: error de validación
    else Datos válidos
        eRec-->>cR: no existe
        cR->>eRec: insertarLinea(producto_id, insumo_id, cantidad)
        eRec-->>cR: línea creada
        cR-->>iR: redirigir a "Gestionar receta" + éxito
    end
    iR-->>Admin: receta actualizada
```

---

## CU-11 — Eliminar Insumo de Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Recetas
    participant cR as c_Recetas
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iR: click "Eliminar" en la fila del insumo
    iR->>Admin: solicita confirmación
    Admin->>iR: confirma
    iR->>cR: eliminarInsumo(producto_id, linea_id)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eRec: eliminarLinea(linea_id, producto_id)
    alt La línea pertenece a la receta
        eRec-->>cR: línea eliminada
        cR-->>iR: redirigir + "insumo eliminado de la receta"
    else Línea inconsistente
        eRec-->>cR: sin coincidencia
        cR-->>iR: aviso de inconsistencia
    end
    iR-->>Admin: receta actualizada
```

---

## CU-12 — Editar Insumo de Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Recetas
    participant cR as c_Recetas
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
        alt Línea pertenece al producto
            eRec-->>cR: cantidad actualizada
            cR-->>iR: redirigir + "cantidad actualizada"
        else Línea inconsistente
            eRec-->>cR: sin coincidencia
            cR-->>iR: aviso de inconsistencia
        end
    end
    iR-->>Admin: receta actualizada
```

---

## CU-08 — Eliminar Receta

```mermaid
sequenceDiagram
    actor Admin as Administrador
    participant iR as i_Recetas
    participant cR as c_Recetas
    participant eProd as e_producto
    participant eRec as e_receta

    Admin->>iR: click "Eliminar receta completa"
    iR->>Admin: solicita confirmación
    Admin->>iR: confirma
    iR->>cR: eliminarReceta(producto_id)
    cR->>eProd: validarProductoDelTenant(producto_id, restaurante_id)
    eProd-->>cR: producto válido
    cR->>eRec: eliminarTodasLasLineas(producto_id)
    alt La receta tenía insumos
        eRec-->>cR: n líneas eliminadas
        cR-->>iR: redirigir + "receta eliminada"
    else El producto no tenía receta
        eRec-->>cR: 0 líneas
        cR-->>iR: aviso "no había receta que eliminar"
    end
    iR-->>Admin: producto queda sin receta (vendible sin descuento)
```
