# Implementation Plan: 005-ui-interaction

**Feature**: Interfaz e interacción con JavaScript (HU-15, HU-16)
**Entrada**: `spec.md`
**Prerrequisito**: Incrementos 1 a 4 implementados.
**Stack**: Flask + SQLAlchemy + Alembic + Jinja2 + JavaScript del navegador, sin framework SPA.

---

## 1. Estrategia de JavaScript para la interacción sin recarga

Se usa **`fetch` nativo** contra el endpoint de cambio de estado ya existente (`POST /tasks/<id>/status`), enviando `Accept: application/json` para recibir la respuesta JSON que ese endpoint ya sabe producir desde el Incremento 1. **No se introduce ningún endpoint nuevo para HU-15** (FR-002).

**Por qué no se añade ningún framework**: la interacción consiste en una petición y la actualización de un par de nodos del DOM. Introducir React o Vue por esto significaría un paso de compilación, un árbol de dependencias y una segunda forma de renderizar la misma página que ya genera Jinja2 — todo ello para sustituir unas pocas líneas de `fetch`. La restricción técnica del stack lo prohíbe por defecto y aquí no hay nada que lo justifique.

**Mejora progresiva (FR-005)**: los controles se siguen renderizando como formularios HTML normales. El script **intercepta** su `submit`; si el script no carga o JavaScript está deshabilitado, el formulario se envía como siempre y la operación funciona con recarga. La funcionalidad nunca depende del JavaScript, solo la fluidez.

**Manejo del error y reversión (FR-003)**: el cambio visual es optimista pero **reversible**. Antes de enviar la petición se guarda el estado visual anterior (texto y clase del distintivo). Si `fetch` rechaza, o si la respuesta no es `ok`, se restaura ese estado exacto y se muestra un mensaje de error. Nunca se deja la interfaz afirmando algo que el backend no confirmó.

**Preservación de filtros (FR-004)**: al no recargar, la URL no cambia y los filtros activos se conservan por construcción.

---

## 2. Técnica elegida para arrastrar y soltar

Se usa la **API de Drag and Drop nativa del navegador** (`draggable`, `dragstart`, `dragover`, `drop`), sin ninguna librería de terceros.

**Por qué no una librería**: SortableJS y equivalentes aportan animaciones y soporte táctil que no son requisitos de este incremento. La API nativa cubre el caso de uso completo —reordenar una lista vertical con el ratón— sin añadir dependencias ni peso. Esto mantiene el proyecto dentro del límite de "sin framework SPA pesado" de la constitución sin necesidad de ninguna justificación adicional.

**Limitación conocida y aceptada**: la API nativa de arrastre no funciona en pantallas táctiles sin un gestor adicional de eventos. El alcance de este incremento no incluye el soporte táctil, y el reordenamiento es una comodidad, no la única vía de organizar tareas: la ordenación por prioridad y fecha límite del Incremento 3 sigue disponible para todo el mundo.

**Cuándo se ofrece (FR-012)**: solo cuando no hay un `sort` explícito en la URL. Permitir arrastrar mientras está activo "ordenar por prioridad" mostraría un orden que la siguiente recarga desharía.

---

## 3. El único cambio de backend: la posición persistente

### 3.1. Modelo

| Campo | Tipo | Restricciones |
|---|---|---|
| `position` | `Integer` | Not Null, Default `0`, Index |

Entero ascendente: a menor valor, más arriba. El orden es **por usuario**, porque cada tarea pertenece a un único propietario y las posiciones solo se comparan entre tareas del mismo `user_id` (FR-009).

### 3.2. Endpoint

`POST /tasks/reorder`, detallado en `contracts/reorder-contracts.md`. Recibe la lista ordenada de identificadores de tarea y reasigna las posiciones de forma consecutiva.

### 3.3. Orden del listado

El orden por defecto del listado pasa a ser `position ASC`, con `created_at DESC` como criterio de desempate para las tareas que compartan posición. Los ordenamientos explícitos del Incremento 3 (`priority_desc`, `priority_asc`, `due_date`) siguen teniendo precedencia cuando se solicitan.

---

## 4. Concurrencia y aislamiento (FR-010, Principio VII)

El orden es **por usuario**, no global, así que dos personas reordenando a la vez no compiten por las mismas filas.

La validación de propiedad se aplica igual que en todos los endpoints anteriores: el servicio filtra los identificadores recibidos contra las tareas del usuario autenticado **antes** de escribir nada. Un identificador ajeno simplemente no aparece en el conjunto a actualizar — no basta con confiar en que el frontend solo envíe los suyos.

Las tareas que ya no existen o fueron eliminadas lógicamente se ignoran en lugar de hacer fallar la operación completa, según el Edge Case correspondiente.

---

## 5. Migración (Principio VI)

Una migración añade `tasks.position` con `server_default='0'`.

**Preservación del orden existente (FR-011, SC-005)**: todas las tareas preexistentes quedan con `position = 0`. Como el desempate es `created_at DESC`, el listado conserva exactamente el orden que tenía antes de la migración hasta que el usuario arrastre algo por primera vez. No hace falta rellenar posiciones una por una en la migración.

---

## 6. Estrategia de pruebas (Principio IV)

**Automatizadas, a nivel de servicio y de ruta** — es donde está el riesgo de pérdida o corrupción de datos:
- Persistir un nuevo orden actualiza las posiciones de **todas** las tareas afectadas.
- El orden persiste entre consultas sucesivas.
- Los identificadores de otros usuarios **no** alteran ninguna posición.
- Los identificadores inexistentes o de tareas eliminadas se ignoran sin romper la operación.
- Las tareas preexistentes conservan su orden relativo con la posición por defecto.
- El endpoint exige sesión activa.

**Manual, para la capa de JavaScript**: **el proyecto no tiene infraestructura de pruebas de frontend** (no hay Jest, Vitest ni Playwright, ni están en `requirements.txt`). Montar una introduciría un ecosistema de Node entero en un proyecto que hasta ahora es solo Python, lo cual excede el alcance de este incremento.

En consecuencia, estos dos comportamientos se verifican **a mano** y así queda declarado:
1. Que un error del backend revierte el estado visual (reproducible deteniendo el servidor y pulsando completar).
2. Que el arrastre reordena y el orden sobrevive a una recarga.

El `quickstart.md` recoge ambos procedimientos paso a paso.
