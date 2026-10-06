# Feature Specification: 004-user-collaboration

**Feature Branch**: `004-user-collaboration`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Especifica el cuarto incremento funcional de TaskControl: colaboración entre usuarios. Este incremento cubre HU-10 y HU-11 del backlog, y asume que los Incrementos 1 a 3 ya están implementados."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asignación Segura de Tareas entre Usuarios (HU-10) (Priority: P1)

Como creador de una tarea, quiero asignarla a otro usuario registrado en la plataforma indicando su identificador o correo electrónico, para delegar trabajo y permitir que el usuario asignado visualice y gestione la tarea desde su propio listado, manteniendo un registro auditable del cambio.

**Why this priority**: Es la base de la colaboración en TaskControl. Transforma el sistema de un gestor unipersonal a una herramienta compartida de equipo.

**Independent Test**: Puede probarse creando una tarea con el Usuario A, asignándola al Usuario B (comprobando que el correo de B exista en el sistema), verificando que el Usuario B vea la tarea en su listado con un badge de "Asignada a mí", y verificando que el evento `TASK_ASSIGNED` quede registrado en el log de auditoría.

**Acceptance Scenarios**:
1. **Given** un usuario autenticado (Usuario A) propietario de una tarea activa y otro usuario registrado en el sistema (Usuario B), **When** el Usuario A asigna la tarea al Usuario B, **Then** la tarea queda vinculada al Usuario B, se emite un log de auditoría con la acción `TASK_ASSIGNED` y se crea una notificación interna para el Usuario B.
2. **Given** un intento de asignación a una dirección de correo electrónico que NO está registrada en el sistema, **When** el usuario envía la solicitud, **Then** el sistema rechaza la asignación en el backend con un mensaje de error claro indicando que el usuario destinatario no existe, sin alterar la tarea ni emitir logs de asignación.
3. **Given** un usuario autenticado (Usuario B) que tiene tareas asignadas por terceros y tareas creadas por sí mismo, **When** accede a su listado de tareas (`/tasks`), **Then** visualiza ambos tipos de tareas con distinción visual clara (etiquetas "Creada por mí" vs "Asignada por [correo del creador]"), pudiendo además filtrar por pestaña ("Todas", "Creadas por mí", "Asignadas a mí").
4. **Given** una tarea asignada, **When** el creador decide retirar la asignación (desasignar), **Then** la tarea vuelve a quedar sin asignatario específico (`assigned_to_id = NULL`), visible únicamente para su creador, y se audita el cambio.
5. **Given** una tarea perteneciente al Usuario A, **When** un Usuario C (no creador) intenta reasignarla a otra persona, **Then** el sistema rechaza la operación por falta de permisos (403 Forbidden).

---

### User Story 2 - Notificaciones Internas de Asignación (HU-11) (Priority: P1)

Como usuario del sistema, quiero recibir una notificación interna dentro de la aplicación cada vez que alguien me asigne una tarea, para enterarme oportunamente sin tener que buscar manualmente en todo el listado de tareas.

**Why this priority**: Completa la experiencia colaborativa cerrando el ciclo de retroalimentación en tiempo real dentro del monolito sin depender de servicios externos de mensajería.

**Independent Test**: Puede probarse asignando una tarea al Usuario B y luego iniciando sesión como Usuario B para verificar:
1. La presencia de un indicador visual (contador badge) de notificaciones no leídas en la barra de navegación.
2. La existencia de la notificación en la vista `/notifications` con el detalle de la tarea y quién la asignó.
3. El marcado de la notificación como leída y la verificación de que permanezca accesible en el historial (persistencia sin descarte).

**Acceptance Scenarios**:
1. **Given** un usuario al que se le acaba de asignar una tarea, **When** navega por la aplicación, **Then** observa un contador de notificaciones no leídas en el encabezado del sistema.
2. **Given** un usuario que accede a su centro de notificaciones (`/notifications`), **When** consulta la lista, **Then** visualiza las notificaciones pendientes con el título de la tarea, el correo del usuario asignador y la fecha/hora de asignación.
3. **Given** una notificación no leída, **When** el usuario hace clic en ella o pulsa "Marcar como leída", **Then** la notificación cambia su estado a leída (`is_read = true`), el contador no leído se decrementa y la notificación **permanece almacenada** en el listado para consulta histórica posterior.
4. **Given** múltiples notificaciones pendientes, **When** el usuario pulsa "Marcar todas como leídas", **Then** todas las notificaciones pendientes del usuario se actualizan a leídas de manera atómica.
5. **Given** un usuario intentando acceder o marcar una notificación dirigida a otro usuario, **When** envía la solicitud, **Then** el sistema responde con 404 Not Found o 403 Forbidden impidiendo la visualización o alteración no autorizada.

---

### Edge Cases

- **Autoasignación**: Si un creador se asigna una tarea a sí mismo (`assigned_to_id == user_id`), la asignación se procesa exitosamente pero el sistema NO genera una notificación interna innecesaria para evitar ruido al propio actor.
- **Reasignación sucesiva**: Si una tarea asignada al Usuario B es reasignada posteriormente al Usuario C, se genera una nueva notificación para el Usuario C y el Usuario B deja de ver la tarea en su pestaña de "Asignadas a mí".
- **Eliminación lógica de tarea asignada**: Si una tarea asignada es eliminada lógicamente por su creador, deja de mostrarse en los listados activos de ambos usuarios; las notificaciones históricas previas preservan el texto del evento sin romper enlaces.
- **Intento de inyección de ID de usuario inexistente o eliminado**: Toda asignación valida activamente contra la base de datos la existencia y vigencia del usuario destino antes de confirmar la transacción.
- **Concurrencia en marcado de lectura**: Si dos pestañas marcan la misma notificación como leída simultáneamente, la operación es idempotente y no genera inconsistencias en el contador.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir al creador de una tarea asignar dicha tarea a otro usuario registrado en el sistema mediante su correo electrónico o identificador.
- **FR-002**: El sistema DEBE validar obligatoriamente en el backend que el usuario asignatario exista en la base de datos antes de efectuar cualquier asignación; queda prohibido delegar esta validación exclusivamente a controles del frontend.
- **FR-003**: El sistema DEBE permitir retirar la asignación de una tarea (dejarla sin usuario asignado).
- **FR-004**: El sistema DEBE incluir las tareas asignadas en el listado principal de tareas (`/tasks`) del usuario asignatario, permitiéndole interactuar con ellas según las reglas de negocio.
- **FR-005**: El sistema DEBE distinguir visualmente en el listado de tareas entre las tareas creadas por el usuario autenticado y las tareas que le han sido asignadas por otros usuarios (mediante badges identificadores).
- **FR-006**: El sistema DEBE proveer en el listado de tareas un mecanismo de filtrado por autoría/asignación con tres opciones: "Todas" (por defecto), "Creadas por mí" y "Asignadas a mí".
- **FR-007**: El sistema DEBE registrar un evento de auditoría estructurado con la acción `TASK_ASSIGNED` ante cada asignación o reasignación, especificando `actor_id`, `entity_id` (tarea), `timestamp` y detalles del usuario asignado.
- **FR-008**: El sistema DEBE generar automáticamente una notificación interna dirigida al usuario asignatario cada vez que se le asigne una tarea (salvo si el creador se autoasigna la tarea).
- **FR-009**: Las notificaciones DEBEN residir y gestionarse exclusivamente dentro de la aplicación y su base de datos relacional, sin recurrir a pasarelas externas de correo ni servicios push externos.
- **FR-010**: El sistema DEBE permitir al usuario consultar el listado de sus notificaciones en la ruta `/notifications`, ordenadas de forma cronológica descendente.
- **FR-011**: El sistema DEBE exponer un contador de notificaciones no leídas en la interfaz principal para usuarios autenticados.
- **FR-012**: El sistema DEBE permitir marcar una notificación individual o todas las notificaciones como leídas (`is_read = true`, registrando `read_at`).
- **FR-013**: Las notificaciones leídas DEBEN persistir en la base de datos para consulta histórica y NO deben ser descartadas ni eliminadas tras su lectura.
- **FR-014**: El sistema DEBE garantizar el aislamiento estricto de notificaciones: ningún usuario puede ver o modificar notificaciones pertenecientes a terceros.

---

### Exclusiones Explícitas (Fuera de Alcance)

- Interacción asíncrona sin recarga de página para completar o mover tareas (`HU-15`).
- Reordenamiento visual mediante arrastrar y soltar (drag and drop) (`HU-16`).
- Notificaciones vía correo electrónico externo (SMTP/SaaS) o notificaciones web push del navegador.
- Asignación múltiple (una tarea solo puede estar asignada a un único usuario a la vez).

---

### Key Entities

- **Task (Actualización)**:
  - Atributos relacionados con asignación:
    - `assigned_to_id`: Clave foránea a `User`, nullable, indexada. Representa al usuario que tiene asignada la ejecución de la tarea.
    - Relación con User: `creator` (`user_id`) y `assignee` (`assigned_to_id`).
- **Notification (Nueva Entidad)**:
  - Representa un aviso interno generado para un usuario ante un evento relevante.
  - Atributos:
    - `id`: Entero PK, autoincremental.
    - `recipient_id`: FK a `users.id` (not null, index). Usuario que recibe la notificación.
    - `sender_id`: FK a `users.id` (not null). Usuario que originó el evento.
    - `task_id`: FK a `tasks.id` (nullable o set null en caso de borrado).
    - `message`: Cadena de texto obligatoria (máx 255 caracteres).
    - `is_read`: Booleano (not null, default `False`, index).
    - `read_at`: Timestamp UTC (nullable).
    - `created_at`: Timestamp UTC (not null, default UTC).
- **AuditLog**:
  - Incorpora la acción `TASK_ASSIGNED` (y `TASK_UNASSIGNED` en caso de retiro de asignación).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% de asignaciones permitidas hacia correos o IDs de usuarios que no existan en la base de datos (rechazo del 100% de peticiones inválidas en backend).
- **SC-002**: El 100% de las tareas asignadas son visibles para el usuario destinatario en su pestaña "Asignadas a mí".
- **SC-003**: El 100% de las asignaciones exitosas a terceros generan una notificación interna persistida en menos de 100ms.
- **SC-004**: Las notificaciones leídas conservan una tasa de retención del 100% en el historial del usuario (0% de borrado no intencionado tras lectura).
- **SC-005**: El 100% de los cambios de asignación quedan registrados en el log de auditoría con actor, tarea, destinatario y fecha UTC.
- **SC-006**: Cobertura de pruebas automatizadas del 100% en las reglas de autorización y persistencia de notificaciones antes del despliegue.

---

## Assumptions

- Toda tarea tiene un único creador inmutable (`user_id`) y un único usuario asignado opcional (`assigned_to_id`).
- Las notificaciones internas se sirven mediante vistas renderizadas en servidor con Jinja2 y llamadas tradicionales/Fetch para marcar lectura, en plena coherencia con la arquitectura del monolito.
- La distinción visual en el listado de tareas se implementa mediante etiquetas contextuales claras y pestañas de filtrado ("Todas", "Creadas por mí", "Asignadas a mí").
- Si el creador de una tarea se la asigna a sí mismo, la tarea queda asignada pero no se genera notificación para evitar redundancia.
