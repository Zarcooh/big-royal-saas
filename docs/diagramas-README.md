# Diagramas del módulo de Recetas / Productos

Diagramas de **colaboración** (`docs/diagramas-colaboracion/`), **actividad**
(`docs/diagramas-actividad/`) y **secuencia** (`docs/diagramas-secuencia/`), todos
en formato **draw.io** (`.drawio`, editables en <https://app.diagrams.net>), con
el formato del docente:

- **Colaboración:** robustez BCE — Administrador (actor) + `i_` (boundary),
  `c_` (control), `e_` (entity), con mensajes `metodo()`.
- **Actividad:** inicio ● → acciones → decisiones (`¿…?` con ramas *sí/no*) → fin.
- **Secuencia:** líneas de vida BCE (`i_`/`c_`/`e_`), mensajes de llamada
  (flecha sólida) y retorno (flecha punteada), y fragmentos `alt` con su guarda.

## Diagramas incluidos

### Recetas (CU-08, CU-10, CU-11, CU-12)
- CU-08 Eliminar Receta
- CU-10 Agregar Insumo a Receta
- CU-11 Eliminar Insumo de Receta
- CU-12 Editar Insumo de Receta

### Productos (CU-22, CU-23, CU-24, CU-25)
- CU-22 Listar Productos
- CU-23 Agregar Producto
- CU-24 Editar Producto
- CU-25 Eliminar Producto

> Módulo de Productos **completo** (colaboración + actividad de los 4 CU).

### Secuencia — también incluye la venta (CU-15)
La carpeta `docs/diagramas-secuencia/` tiene los `.drawio` de secuencia de
CU-08/10/11/12 y CU-22/23/24/25, más **CU-15 Registrar Venta**. (Antes estaban
en Mermaid; se pasaron a draw.io para unificar formato con los demás.)

## Casos de uso eliminados (sin diagrama)

CU-06 (Listar Recetas), CU-07 (Agregar Recetas) y CU-09 (Editar Receta) se
**eliminaron** del modelo; su función la cubren CU-22, CU-10 y CU-12
respectivamente. No llevan diagrama.

## Nota sobre las figuras

Las figuras BCE se armaron con formas estándar de draw.io (elipses + la barra de
boundary y el subrayado de entity como líneas). draw.io tiene en su sección
**UML** las figuras de robustez exactas: si el docente exige ese glifo, se puede
seleccionar cada círculo y cambiar su forma desde ahí; las etiquetas, mensajes y
el layout ya están listos.
