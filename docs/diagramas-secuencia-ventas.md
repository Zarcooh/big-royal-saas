# Diagramas de secuencia — Módulo Ventas

Diagrama de secuencia del caso de uso de venta, basado en la implementación real
(`app/routes/ventas.py` + la RPC `registrar_venta_multiple`, migración 010).
Convención boundary-control-entity, como el resto de los diagramas:

- **`i_`** interfaz (boundary): la pantalla de venta.
- **`c_`** control: el blueprint/controlador de ventas.
- **`f_`** función de base de datos (RPC transaccional).
- **`e_`** entidad: las tablas de la base.

> Se renderiza automáticamente en GitHub. Para el informe puedes exportarlo a
> imagen desde <https://mermaid.live>.

---

## CU-15 — Registrar Venta (carrito + auto-descuento)

La venta **exige** que todos los productos tengan receta (regla reforzada en la
migración 010): un producto sin receta bloquea el pedido completo. Todo el
descuento ocurre dentro de la RPC transaccional; si algo falla, no se registra
nada (RNF-REL-01). Incluye el auto-descuento de stock (CU-16).

```mermaid
sequenceDiagram
    actor Caj as Cajero
    participant iV as i_Venta
    participant cV as c_Venta
    participant fRPC as f_registrarVentaMultiple
    participant eProd as e_producto
    participant eRec as e_receta
    participant eIns as e_insumo
    participant eVen as e_venta

    Caj->>iV: indicar cantidad y "Agregar" por producto
    iV->>cV: agregarAlCarrito(producto_id, cantidad)
    cV-->>iV: pedido actualizado (carrito en sesión)
    iV-->>Caj: muestra detalle del pedido y total

    Caj->>iV: click "Confirmar compra"
    iV->>cV: confirmar()
    cV->>fRPC: registrar_venta_multiple(items)
    fRPC->>eProd: validar productos del tenant (RN03)
    fRPC->>eRec: ¿todos los productos tienen receta?

    alt Algún producto sin receta
        fRPC-->>cV: EXCEPTION PRODUCTO_SIN_RECETA
        cV-->>iV: aviso "sin receta: no se puede vender"
        iV-->>Caj: pedido NO registrado
    else Todos con receta
        fRPC->>eIns: bloquear filas y verificar stock por insumo (FOR UPDATE)
        alt Falta stock de algún insumo
            fRPC-->>cV: EXCEPTION STOCK_INSUFICIENTE
            cV-->>iV: aviso "stock insuficiente"
            iV-->>Caj: pedido NO registrado (nada cambia)
        else Stock suficiente
            fRPC->>eIns: descontar stock + registrar en auditoría (CU-16)
            fRPC->>eVen: crear venta + detalle de venta
            fRPC-->>cV: venta_id
            cV->>eVen: leer comprobante (venta + detalle)
            cV->>eIns: leer stock actualizado
            cV-->>iV: comprobante (detalle + stock descontado)
            iV-->>Caj: "Venta registrada y stock actualizado"
        end
    end
```

---

## Notas

- **Atomicidad (RNF-REL-01):** toda la operación (validaciones, descuento,
  inserción de venta/detalle y auditoría) corre dentro de la RPC en una sola
  transacción. Cualquier excepción revierte el pedido completo: nunca queda media
  venta ni un inventario descuadrado.
- **CU-16 (Auto-descuento):** no es una pantalla, ocurre dentro de este mismo
  flujo (paso "descontar stock + registrar en auditoría").
- **Sin escape:** ya no existe el "continuar de todos modos"; un producto sin
  receta siempre bloquea la venta.
