# Contratos de Endpoints: Cierre del Ciclo de Tareas (HU-05 y HU-06)

**Blueprint**: `tasks_bp` (`/tasks`)  
**Cumplimiento**: Principio III (Contrato explícito), Principio VI (Integridad y soft delete), Principio VII (Verificación de sesión en backend) y Principio VIII (Observabilidad y log estructurado).

---

## 1. Eliminación Lógica de Tareas (`HU-05`)

### 1.1. `POST /tasks/<int:task_id>/delete` (o `DELETE /tasks/<int:task_id>`)
Marca una tarea como eliminada lógicamente (`is_deleted=True`), registrando fecha de eliminación y evento de auditoría `TASK_DELETED`.

- **Método**: `POST` (soporta también `DELETE` en peticiones Fetch/API)
- **Ruta**: `/tasks/<int:task_id>/delete`
- **Autenticación**: **Obligatoria** (sesión activa en backend).
- **Headers**:
  - `Content-Type: application/json` o `application/x-www-form-urlencoded`
  - `Accept: application/json` o `text/html`
- **Payload de Entrada**: Vacío (o token CSRF en formularios HTML).

#### Respuestas:

- **`200 OK` (Éxito JSON)**:
  ```json
  {
    "status": "success",
    "message": "Tarea eliminada exitosamente",
    "data": {
      "task_id": 101,
      "is_deleted": true,
      "deleted_at": "2026-10-01T15:30:00Z"
    }
  }
  ```
- **`302 Found` (Éxito HTML)**: Redirección a `/tasks` con mensaje flash informativo.
- **`401 Unauthorized`**: Sesión ausente o expirada.
- **`404 Not Found`**: La tarea no existe o pertenece a otro usuario (aislamiento por seguridad).
- **`400 Bad Request` / `409 Conflict`**: La tarea ya se encuentra en estado eliminado (no se permite doble eliminación).
  ```json
  {
    "status": "error",
    "code": "TASK_ALREADY_DELETED",
    "message": "La tarea ya fue eliminada previamente"
  }
  ```

---

## 2. Reapertura de Tareas Completadas (`HU-06`)

### 2.1. `POST /tasks/<int:task_id>/reopen`
Devuelve una tarea en estado `completed` al estado activo inicial `pending`, registrando el evento `TASK_REOPENED` en el log de auditoría.

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/reopen`
- **Autenticación**: **Obligatoria** (sesión activa en backend).
- **Headers**:
  - `Content-Type: application/json` o `application/x-www-form-urlencoded`
  - `Accept: application/json` o `text/html`
- **Payload de Entrada**: Vacío (o token CSRF en formularios HTML).

#### Respuestas:

- **`200 OK` (Éxito JSON)**:
  ```json
  {
    "status": "success",
    "message": "Tarea reabierta exitosamente",
    "data": {
      "task_id": 101,
      "status": "pending",
      "previous_status": "completed",
      "updated_at": "2026-10-01T15:35:00Z"
    }
  }
  ```
- **`302 Found` (Éxito HTML)**: Redirección a `/tasks` con mensaje flash informativo.
- **`401 Unauthorized`**: Sesión no válida.
- **`404 Not Found`**: La tarea no existe o pertenece a otro usuario.
- **`400 Bad Request`**: La tarea no se puede reabrir porque su estado no es `completed` o porque está eliminada.
  ```json
  {
    "status": "error",
    "code": "INVALID_STATE_FOR_REOPEN",
    "message": "Solo se pueden reabrir tareas que se encuentren en estado 'completada'"
  }
  ```
