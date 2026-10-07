# Contratos de Endpoints: Asignación de Tareas (HU-10)

**Blueprint**: `tasks_bp` (`/tasks`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Solo el creador asigna/desasigna; validación backend del correo destino) y Principio VIII (Auditoría).

---

## 1. Asignar Tarea a un Usuario

### 1.1. `POST /tasks/<int:task_id>/assign`
Asigna (o reasigna) una tarea propia a otro usuario registrado, identificado por correo electrónico (ver spec Clarifications, Session 2026-10-06, Q1).

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/assign`
- **Autenticación**: **Obligatoria**. Solo el creador de la tarea puede ejecutar esta acción.
- **Payload de Entrada**:
  ```json
  {
    "assigned_to_email": "companero@ejemplo.com"
  }
  ```

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Tarea asignada exitosamente",
    "data": {
      "task_id": 101,
      "assigned_to": {"id": 7, "email": "companero@ejemplo.com"}
    }
  }
  ```
- **`400 Bad Request`**: `assigned_to_email` vacío o con formato inválido.
  ```json
  {"status": "error", "code": "VALIDATION_ERROR", "message": "Debe indicar un correo electrónico válido"}
  ```
- **`404 Not Found`**:
  - La tarea no existe o no pertenece al usuario autenticado (código `TASK_NOT_FOUND`).
  - El correo indicado no corresponde a ningún usuario registrado (código `ASSIGNEE_NOT_FOUND`, FR-002).
  ```json
  {"status": "error", "code": "ASSIGNEE_NOT_FOUND", "message": "No existe un usuario registrado con ese correo electrónico"}
  ```
- **`401 Unauthorized`**: Sin sesión activa.

---

## 2. Retirar Asignación

### 2.1. `POST /tasks/<int:task_id>/unassign`
Retira la asignación de una tarea propia. **Nunca** genera notificación (ver spec Clarifications, Session 2026-10-06, Q2).

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/unassign`
- **Autenticación**: **Obligatoria**. Solo el creador puede ejecutar esta acción.
- **Payload de Entrada**: Vacío.

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {"status": "success", "message": "Asignación retirada exitosamente", "data": {"task_id": 101, "assigned_to": null}}
  ```
- **`404 Not Found`**: La tarea no existe o no pertenece al usuario autenticado.
- **`401 Unauthorized`**: Sin sesión activa.

---

## 3. Listado de Tareas con Vista por Rol

### 3.1. `GET /tasks?view=all|created|assigned`
Extiende el listado existente (Incrementos 1-3) con un filtro por rol del usuario respecto a la tarea.

- **Query Parameter nuevo**: `view` *(opcional, default `all`)*:
  - `all`: tareas donde el usuario es creador **o** asignatario.
  - `created`: solo tareas creadas por el usuario.
  - `assigned`: solo tareas asignadas al usuario por otros.
- **Contrato de salida extendido**: cada tarea incluye:
  - `assigned_to`: objeto `{id, email}` o `null`.
  - `is_owner`: booleano (`true` si el usuario autenticado es el creador).
- Resto del contrato (status, sort, category_id, paginación) sin cambios respecto a Incrementos 1-3.
