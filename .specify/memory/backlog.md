# Backlog del Proyecto: TaskControl

**Sistema**: Gestión y control de tareas
**Arquitectura**: Monolito Python (Flask) + JavaScript
**Priorización**: MoSCoW (Must / Should / Could / Won't — este backlog no incluye Won't por ahora)

---

## Épica 1 — Gestión de tareas (núcleo del dominio)

### HU-01 (Must)
**Como** usuario, **quiero** crear una tarea con título, descripción opcional y fecha límite opcional, **para** registrar el trabajo pendiente.

**Criterios de aceptación**:
- El título es obligatorio y no puede estar vacío.
- La tarea se crea con estado inicial "pendiente".
- Se registra el actor y el timestamp de creación en el log de auditoría.

### HU-02 (Must)
**Como** usuario, **quiero** ver el listado de mis tareas, **para** tener visibilidad de lo que tengo pendiente.

**Criterios de aceptación**:
- El listado muestra título, estado y fecha límite.
- Se puede filtrar por estado.
- Solo se muestran tareas del usuario autenticado.

### HU-03 (Must)
**Como** usuario, **quiero** cambiar el estado de una tarea (pendiente → en progreso → completada), **para** reflejar su avance real.

**Criterios de aceptación**:
- Las transiciones válidas están explícitamente definidas.
- No se puede pasar de "completada" a "pendiente" sin una transición explícita de reapertura.
- Cada cambio de estado queda registrado en el log de auditoría.

### HU-04 (Must)
**Como** usuario, **quiero** editar el título, descripción o fecha límite de una tarea existente, **para** corregir información incorrecta.

**Criterios de aceptación**:
- No se permite editar una tarea eliminada.
- Los cambios se validan igual que en la creación.

### HU-05 (Should)
**Como** usuario, **quiero** eliminar una tarea, **para** deshacerme de las que ya no son relevantes.

**Criterios de aceptación**:
- La eliminación es lógica (soft delete), no física, para preservar el log de auditoría.
- Una tarea eliminada no aparece en el listado por defecto.

### HU-06 (Should)
**Como** usuario, **quiero** reabrir una tarea marcada como completada por error, **para** corregir el estado sin perder el historial.

**Criterios de aceptación**:
- La reapertura queda registrada como un evento distinto de la creación original.

---

## Épica 2 — Organización y priorización

### HU-07 (Should)
**Como** usuario, **quiero** asignar una prioridad (alta, media, baja) a cada tarea, **para** decidir en qué orden trabajarlas.

**Criterios de aceptación**:
- La prioridad tiene un valor por defecto.
- El listado se puede ordenar por prioridad.

### HU-08 (Could)
**Como** usuario, **quiero** agrupar tareas en categorías o proyectos, **para** organizar trabajo relacionado.

**Criterios de aceptación**:
- Una tarea pertenece a máximo una categoría.
- Eliminar una categoría no elimina sus tareas (quedan sin categoría).

### HU-09 (Could)
**Como** usuario, **quiero** recibir una indicación visual de las tareas vencidas (fecha límite superada sin completar), **para** priorizar su atención.

**Criterios de aceptación**:
- El cálculo se hace en el backend, no en JavaScript, para evitar inconsistencias por zona horaria del cliente.

---

## Épica 3 — Colaboración

### HU-10 (Should)
**Como** usuario, **quiero** asignar una tarea a otro usuario del sistema, **para** delegar trabajo.

**Criterios de aceptación**:
- Solo se puede asignar a usuarios existentes.
- El usuario asignado ve la tarea en su propio listado.
- El cambio de asignación queda auditado.

### HU-11 (Could)
**Como** usuario asignado, **quiero** recibir una notificación (interna, dentro de la app) cuando se me asigna una tarea, **para** enterarme sin tener que revisar manualmente.

---

## Épica 4 — Cuentas y acceso

### HU-12 (Must)
**Como** usuario nuevo, **quiero** registrarme con correo y contraseña, **para** tener acceso al sistema.

**Criterios de aceptación**:
- La contraseña se almacena con hash (nunca en texto plano).
- Se valida formato de correo y unicidad.

### HU-13 (Must)
**Como** usuario registrado, **quiero** iniciar y cerrar sesión, **para** proteger el acceso a mis tareas.

**Criterios de aceptación**:
- Las rutas que modifican tareas verifican sesión activa en el backend, no solo ocultan botones en el frontend.

### HU-14 (Should)
**Como** usuario, **quiero** recuperar mi contraseña si la olvido, **para** no perder acceso permanentemente.

---

## Épica 5 — Interfaz e interacción (JavaScript)

### HU-15 (Should)
**Como** usuario, **quiero** marcar una tarea como completada sin recargar la página, **para** una experiencia fluida.

**Criterios de aceptación**:
- La interacción usa el contrato de endpoint definido entre backend y JavaScript.
- Si la petición falla, la interfaz revierte el cambio visual y muestra un error.

### HU-16 (Could)
**Como** usuario, **quiero** reordenar tareas arrastrándolas (drag and drop), **para** ajustar prioridad visualmente.

**Criterios de aceptación**:
- El nuevo orden se persiste en el backend tras soltar el elemento.

---

## Resumen de priorización

| Prioridad | Historias |
|---|---|
| Must | HU-01, HU-02, HU-03, HU-04, HU-12, HU-13 |
| Should | HU-05, HU-06, HU-07, HU-10, HU-14, HU-15 |
| Could | HU-08, HU-09, HU-11, HU-16 |

**Recomendación de primer incremento**: HU-01 a HU-04 + HU-12–HU-13 (gestión básica de tareas + autenticación), como base coherente con el principio de simplicidad de la constitución del proyecto antes de abrir colaboración o interacción avanzada.
