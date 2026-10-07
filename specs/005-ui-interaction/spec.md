# Feature Specification: 005-ui-interaction

**Feature Branch**: `005-ui-interaction`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Especifica el quinto y último incremento funcional de TaskControl: mejoras de interacción en el frontend mediante JavaScript. Este incremento cubre HU-15 y HU-16 del backlog, y asume que todos los incrementos anteriores (1 a 4) ya están implementados y expuestos como endpoints HTTP con contrato definido."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Completar Tareas sin Recargar la Página (HU-15) (Priority: P1)

Como usuario con un listado largo de tareas, quiero marcar una tarea como completada sin que la página se recargue entera, para no perder mi posición en el listado ni los filtros que tenía aplicados.

**Why this priority**: Es la interacción más frecuente del sistema. Recargar la página completa en cada cambio de estado hace que el usuario pierda el contexto visual y los filtros activos en cada clic.

**Independent Test**: Puede probarse aplicando un filtro, desplazándose hasta una tarea del final del listado, marcándola como completada y comprobando que el distintivo de estado cambia en el sitio, sin recarga y sin perder ni el filtro ni la posición del desplazamiento.

**Acceptance Scenarios**:
1. **Given** un usuario autenticado viendo su listado de tareas, **When** pulsa el control de completar de una tarea pendiente o en progreso, **Then** el distintivo de estado de esa tarea cambia a "Completada" sin que la página se recargue, y el resto del listado permanece intacto.
2. **Given** una petición de cambio de estado que **falla** en el backend (error de red, sesión expirada o transición no permitida), **When** el backend responde con error, **Then** la interfaz **revierte** el cambio visual al estado anterior y muestra al usuario un mensaje de error explicando qué ocurrió.
3. **Given** un usuario con filtros aplicados (estado, categoría, ámbito u orden), **When** completa una tarea sin recargar, **Then** los filtros y el ordenamiento seleccionados se conservan tal cual estaban.
4. **Given** un navegador con JavaScript deshabilitado o un fallo al cargar el script, **When** el usuario pulsa el control de completar, **Then** el formulario se envía de la forma tradicional y la operación se completa igualmente con recarga de página.
5. **Given** una tarea que el usuario no creó (asignada a él), **When** se renderiza el listado, **Then** no se le ofrece el control de completar, en coherencia con las reglas de autorización del Incremento 4.

---

### User Story 2 - Reordenar Tareas Arrastrándolas (HU-16) (Priority: P2)

Como usuario que organiza su trabajo por criterio propio, quiero reordenar visualmente mis tareas arrastrándolas, para establecer un orden personal que no dependa de la fecha de creación ni de la prioridad.

**Why this priority**: Aporta control sobre la presentación, pero depende de que la interacción básica sin recarga (HU-15) ya funcione.

**Independent Test**: Puede probarse arrastrando una tarea desde el final del listado hasta la primera posición, recargando la página después y comprobando que el nuevo orden se mantiene.

**Acceptance Scenarios**:
1. **Given** un usuario viendo su listado de tareas sin ordenamiento explícito aplicado, **When** arrastra una tarea y la suelta en otra posición, **Then** el listado refleja el nuevo orden inmediatamente y este se persiste en el backend.
2. **Given** un usuario que acaba de reordenar sus tareas, **When** recarga la página o vuelve a entrar más tarde, **Then** el orden personal que definió se conserva.
3. **Given** una petición de reordenamiento que **falla** en el backend, **When** el backend responde con error, **Then** la interfaz devuelve las tareas a su orden anterior y avisa al usuario.
4. **Given** un usuario que tiene aplicado un ordenamiento explícito (por prioridad o por fecha límite), **When** consulta el listado, **Then** **no** se ofrece el reordenamiento manual, porque entraría en conflicto con el criterio de ordenamiento activo.
5. **Given** un usuario intentando reordenar una tarea que no le pertenece, **When** envía la petición, **Then** el backend rechaza la operación sin alterar ninguna tarea ajena.

---

### Edge Cases

- **Orden es por usuario, no global**: dos usuarios reordenando sus respectivas tareas en paralelo no interfieren entre sí, porque cada posición se almacena asociada a las tareas de un único propietario.
- **Tareas preexistentes sin posición asignada**: las tareas creadas en los Incrementos 1 a 4 no tienen un orden personal definido; deben recibir un valor por defecto coherente que preserve el orden actual (el de creación) hasta que el usuario reordene.
- **Tarea eliminada durante el arrastre**: si una tarea deja de existir entre el renderizado y el soltar, la operación de reordenamiento ignora ese identificador en vez de fallar por completo.
- **Identificadores ajenos en la petición de reordenamiento**: si la lista enviada incluye el identificador de una tarea de otro usuario, el backend la ignora y no altera su posición.
- **Doble envío por arrastre accidental**: soltar una tarea en la misma posición en la que estaba no debe generar una petición innecesaria al backend.
- **Fallo de red a mitad del reordenamiento**: el orden visual vuelve al anterior; no queda un estado intermedio que el backend no haya confirmado.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir marcar una tarea como completada desde el listado mediante JavaScript, sin recargar la página completa.
- **FR-002**: La interacción sin recarga DEBE consumir el endpoint de cambio de estado **ya existente** del Incremento 1; no se introduce ningún endpoint nuevo para esta historia.
- **FR-003**: Si la petición al backend falla, la interfaz DEBE revertir el cambio visual y mostrar un mensaje de error; NUNCA debe quedar mostrando un estado que el backend no haya confirmado.
- **FR-004**: La interacción sin recarga DEBE preservar los filtros y el ordenamiento activos.
- **FR-005**: El sistema DEBE seguir funcionando sin JavaScript: los controles se renderizan como formularios tradicionales y el script los mejora progresivamente.
- **FR-006**: El sistema DEBE permitir reordenar las tareas del listado mediante arrastrar y soltar.
- **FR-007**: El nuevo orden DEBE persistirse en el backend inmediatamente después de soltar el elemento.
- **FR-008**: El orden personal DEBE conservarse entre sesiones y recargas de página.
- **FR-009**: El sistema DEBE almacenar la posición de orden **por tarea**, siendo el orden propio de cada usuario y no global.
- **FR-010**: El backend DEBE validar la propiedad de cada tarea incluida en una petición de reordenamiento, ignorando o rechazando los identificadores que no pertenezcan al usuario autenticado.
- **FR-011**: Las tareas creadas antes de este incremento DEBEN recibir una posición por defecto que preserve el orden que tenían.
- **FR-012**: El reordenamiento manual solo DEBE ofrecerse cuando no haya un ordenamiento explícito activo (prioridad o fecha límite), para no presentar dos criterios de orden contradictorios.
- **FR-013**: NO se introduce ningún framework SPA (React, Vue, Angular). La interactividad se implementa en JavaScript del navegador, conforme a la restricción técnica del stack.

---

### Exclusiones Explícitas (Fuera de Alcance)

- Actualización en tiempo real entre varias sesiones o pestañas (WebSockets, polling).
- Reordenamiento con teclado o accesible por lector de pantalla como requisito bloqueante de este incremento.
- Edición en línea de otros campos de la tarea sin recarga (título, descripción, fecha).
- Arrastrar tareas entre categorías para reasignarlas.

---

### Key Entities

- **Task (Actualización)**:
  - `position`: Entero, no nulo, con valor por defecto. Define el orden personal del listado dentro de las tareas del mismo propietario.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los cambios de estado exitosos se reflejan en la interfaz sin recargar la página.
- **SC-002**: El 100% de las peticiones fallidas revierten el estado visual: cero casos en los que la interfaz muestre un estado que el backend no confirmó.
- **SC-003**: El 100% de los reordenamientos se conservan tras recargar la página.
- **SC-004**: 0% de posiciones alteradas en tareas pertenecientes a otros usuarios ante peticiones de reordenamiento manipuladas.
- **SC-005**: El 100% de las tareas preexistentes conservan su orden relativo tras la migración.
- **SC-006**: La aplicación conserva toda su funcionalidad con JavaScript deshabilitado.

---

## Assumptions

- El endpoint de cambio de estado del Incremento 1 ya responde JSON cuando la petición lo solicita, por lo que HU-15 no requiere modificarlo.
- El reordenamiento se implementa con la API de arrastrar y soltar nativa del navegador, sin añadir dependencias de terceros.
- La posición se almacena como entero ascendente: a menor valor, más arriba en el listado.
- **No existe infraestructura de pruebas de frontend** en el proyecto (no hay Jest, Vitest ni Playwright). La lógica de JavaScript se verifica **manualmente**; las pruebas automatizadas cubren el contrato del backend —persistencia del orden y autorización—, que es donde reside el riesgo de pérdida de datos.
