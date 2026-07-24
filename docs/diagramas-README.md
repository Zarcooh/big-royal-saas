# Diagramas del módulo de Recetas / Productos

Diagramas de **colaboración** (`docs/diagramas-colaboracion/`) y **actividad**
(`docs/diagramas-actividad/`) en formato **draw.io** (`.drawio`, editables en
<https://app.diagrams.net>), con el formato del docente:

- **Colaboración:** robustez BCE — Administrador (actor) + `i_` (boundary),
  `c_` (control), `e_` (entity), con mensajes `metodo()`.
- **Actividad:** inicio ● → acciones → decisiones (`¿…?` con ramas *sí/no*) → fin.

## Dos opciones para presentar (elige una)

Como el modelo de casos de uso se puede plantear de dos formas, se dejan ambas
para comparar:

### `opcion-7cu/` — numeración original (7 CU)
Un diagrama por cada CU asignado, tal cual la lista original:

- CU-06 Listar Recetas
- CU-07 Agregar Recetas
- CU-08 Eliminar Receta
- CU-09 Editar Receta
- CU-10 Agregar Insumo a Receta
- CU-11 Eliminar Insumo de Receta
- CU-12 Editar Insumo de Receta

### `opcion-5cu/` — modelo unificado (5 CU)
Refleja la app real (no hay pantallas separadas de "crear/editar receta"):

- CU-22 Listar Productos *(sustituye a CU-06 Listar Recetas)*
- CU-08 Eliminar Receta
- CU-10 Agregar Insumo a Receta *(absorbe CU-07 Agregar Receta)*
- CU-11 Eliminar Insumo de Receta
- CU-12 Editar Insumo de Receta *(absorbe CU-09 Editar Receta)*

> CU-08, CU-10, CU-11 y CU-12 son idénticos en ambas opciones; la diferencia es
> que la opción de 5 usa **CU-22 Listar Productos** y descarta CU-06/07/09 como
> CU separados.

## Nota sobre las figuras

Las figuras BCE se armaron con formas estándar de draw.io (elipses + la barra de
boundary y el subrayado de entity como líneas). draw.io tiene en su sección
**UML** las figuras de robustez exactas: si el docente exige ese glifo, se puede
seleccionar cada círculo y cambiar su forma desde ahí; las etiquetas, mensajes y
el layout ya están listos.
