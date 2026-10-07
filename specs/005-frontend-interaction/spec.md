# Feature Specification: 005-frontend-interaction

**Feature Branch**: `005-frontend-interaction`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Especifica el quinto y último incremento funcional de TaskControl: mejoras de interacción en el frontend mediante JavaScript. Este incremento cubre HU-15 y HU-16 del backlog, y asume que todos los incrementos anteriores (1 a 4) ya están implementados y expuestos como endpoints HTTP con contrato definido."

## Clarifications

### Session 2026-10-07

- Q: Cuando un usuario arrastra una tarea a una nueva posición, ¿ese orden se guarda como una posición global única por tarea, o como una posición dentro del filtro/vista que tenía activo? → A: Posición global única por tarea: el orden manual es el mismo sin importar qué filtro de estado/categoría esté activo.
- Q: ¿El arrastrar y soltar debe estar disponible siempre, o solo cuando el usuario está viendo el listado en modo "orden manual" explícito? → A: Solo cuando el usuario tiene seleccionado explícitamente el modo de orden manual (`sort=manual`); con otros criterios de orden activos (prioridad, fecha), las tareas no son arrastrables.
- Q: ¿El usuario puede reordenar manualmente también las tareas que le fueron asignadas (Incremento 4), o el reordenamiento se limita a las tareas que él mismo creó? → A: Puede reordenar cualquier tarea visible en su propio listado, sea creador o asignatario — es una preferencia de vista personal, no una edición de la tarea.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Completar Tareas sin Recargar la Página (HU-15) (Priority: P1)

Como usuario autenticado, quiero marcar una tarea como completada directamente desde el listado mediante una interacción de JavaScript, sin que la página se recargue por completo, para mantener mi contexto visual y trabajar más rápido.

**Why this priority**: Es la mejora de interacción más frecuente (cambio de estado) y la base conceptual sobre la que se apoya la justificación de no introducir un framework SPA — si esto no funciona bien, el resto de la interactividad JS pierde sentido.

**Independent Test**: Puede probarse haciendo clic en la acción de completar una tarea y verificando que el cambio se refleje visualmente sin recarga de página; simulando una falla del backend (ej. desconectando la red o forzando un error) y verificando que la interfaz revierta el cambio visual y muestre un mensaje de error, dejando la tarea en su estado real.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado con una tarea en estado "pendiente" o "en progreso", **When** hace clic en la acción de completar, **Then** la interfaz actualiza visualmente el estado de la tarea sin recargar la página completa, usando el endpoint de cambio de estado ya existente (Incremento 1).
2. **Given** una interacción de completar en curso, **When** la petición al backend responde con éxito, **Then** el estado visual mostrado coincide exactamente con el estado confirmado por el backend.
3. **Given** una interacción de completar en curso, **When** la petición al backend falla (error de red o respuesta de error), **Then** la interfaz revierte el cambio visual al estado anterior y muestra un mensaje de error al usuario — en ningún momento queda visible un estado que el backend no confirmó.

---

### User Story 2 - Reordenar Tareas Arrastrándolas (HU-16) (Priority: P2)

Como usuario autenticado, quiero reordenar visualmente mis tareas en el listado arrastrándolas y soltándolas, para organizar mi propia prioridad visual de trabajo más allá del ordenamiento por fecha o prioridad ya existente.

**Why this priority**: Depende de que la interacción base sin recarga (HU-15) ya esté funcionando, y es una mejora de organización personal, no un flujo crítico del negocio.

**Independent Test**: Puede probarse arrastrando una tarea a una nueva posición del listado, recargando la página por completo, y verificando que el nuevo orden visual se haya mantenido.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado que selecciona explícitamente el modo de orden manual en su listado, **When** arrastra una tarea y la suelta en una nueva posición, **Then** el listado refleja inmediatamente el nuevo orden visual.
2. **Given** una tarea reordenada mediante arrastrar y soltar, **When** la operación de soltar se completa, **Then** el nuevo orden se persiste en el backend sin necesidad de ninguna acción adicional del usuario.
3. **Given** un orden de tareas ya persistido, **When** el usuario recarga la página o vuelve a iniciar sesión más tarde, **Then** el listado se presenta respetando el último orden guardado por ese usuario.
4. **Given** una tarea que no es ni creada ni asignada al usuario autenticado, **When** se intenta persistir un reordenamiento que la incluya, **Then** el backend rechaza la operación por falta de autorización. **Given** una tarea asignada al usuario autenticado (aunque no sea su creador), **When** la reordena, **Then** el backend acepta la operación como una preferencia de vista personal (ver Clarifications, Session 2026-10-07).

---

### Edge Cases

- **Fallo de red durante el cambio de estado (HU-15)**: Ya cubierto explícitamente por el Acceptance Scenario 3 de la Historia 1 — la interfaz nunca muestra un estado no confirmado por el backend.
- **Doble interacción rápida sobre la misma tarea**: Si el usuario completa una tarea y antes de que la petición anterior resuelva intenta otra acción sobre la misma tarea, el backend sigue siendo la única fuente de verdad del estado final — las reglas de transición de estado ya definidas en el Incremento 1 se siguen aplicando sin cambios.
- **Reordenamiento combinado con los criterios de orden existentes (prioridad, fecha)**: El arrastrar y soltar solo está habilitado cuando el usuario tiene seleccionado explícitamente el modo de orden manual; con cualquier otro criterio activo (prioridad, fecha, más reciente) las tareas no son arrastrables, evitando confusión entre lo que se ve y lo que se estaría reordenando (ver Clarifications, Session 2026-10-07).
- **Tareas eliminadas lógicamente**: No participan del reordenamiento manual, igual que ya están excluidas del listado por defecto desde el Incremento 2.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir completar una tarea desde el listado mediante una interacción de JavaScript que invoque el endpoint de cambio de estado ya existente, sin recargar la página completa.
- **FR-002**: Si la petición de cambio de estado falla, el sistema DEBE revertir el cambio visual mostrado y presentar un mensaje de error al usuario; en ningún momento la interfaz muestra un estado no confirmado por el backend.
- **FR-003**: El sistema DEBE permitir a un usuario autenticado reordenar visualmente sus propias tareas en el listado mediante arrastrar y soltar, únicamente cuando el listado está en modo de orden manual explícitamente seleccionado; con cualquier otro criterio de orden activo (prioridad, fecha, más reciente) las tareas no son arrastrables (ver Clarifications, Session 2026-10-07).
- **FR-004**: El sistema DEBE persistir el nuevo orden en el backend inmediatamente después de soltar el elemento, sin requerir una acción de confirmación adicional del usuario.
- **FR-005**: El orden persistido DEBE mantenerse entre sesiones — al recargar la página o volver a iniciar sesión, el listado respeta el último orden guardado. El orden es una posición global única por tarea, la misma sin importar qué filtro de estado o categoría esté activo (ver Clarifications, Session 2026-10-07).
- **FR-006**: El sistema DEBE rechazar en el backend cualquier intento de reordenar una tarea que no sea ni creada ni asignada al usuario autenticado. El reordenamiento de una tarea asignada (no creada) por el usuario SÍ está permitido, al ser una preferencia de vista personal y no una edición del contenido de la tarea (ver Clarifications, Session 2026-10-07).
- **FR-007**: Ninguna de las dos interacciones (completar, reordenar) introduce un endpoint HTTP nuevo salvo el estrictamente necesario para persistir el campo de orden de HU-16 — HU-15 reutiliza exclusivamente el endpoint de cambio de estado ya existente.

### Key Entities

- **Task (Actualización)**: Incorpora un nuevo atributo de orden visual persistente: una posición global única por tarea (no por combinación de filtros), independiente de `priority`, `due_date` y `created_at` ya existentes.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los cambios de estado realizados desde el listado se reflejan visualmente sin recarga completa de la página.
- **SC-002**: 0% de los casos en que una falla del backend deja visible en pantalla un estado de tarea no confirmado por el backend.
- **SC-003**: El 100% de los reordenamientos por arrastrar y soltar persisten correctamente, verificado al recargar la página.
- **SC-004**: 0% de reordenamientos aceptados sobre tareas que no pertenecen al usuario autenticado.

---

## Assumptions

- El orden manual es una preferencia personal por usuario, independiente de los criterios de ordenamiento por prioridad o fecha ya existentes (Incremento 3); ambos coexisten como opciones distintas de visualización.
- Las tareas creadas antes de este incremento reciben un orden inicial razonable (por ejemplo, el mismo orden en que ya se listaban) sin requerir acción manual del usuario.
- Consistente con la restricción técnica del stack (JavaScript vanilla o librería ligera, sin framework SPA salvo justificación explícita), la elección concreta de técnica para el arrastrar y soltar se decide en la planificación técnica, no en esta especificación.
- El endpoint o extensión de endpoint necesario para persistir el orden de HU-16 se define en la planificación técnica; esta especificación solo establece que dicha persistencia debe existir (FR-004, FR-005).
