# Contratos de Endpoints: Gestión de Tareas (HU-01 a HU-04)

**Blueprint**: `tasks_bp` (`/tasks`)  
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Verificación estricta de sesión en backend) y Principio VIII (Observabilidad y log estructurado).

---

## 1. Listado de Tareas (`HU-02`)

### 1.1. `GET /tasks`
Obtiene las tareas exclusivas del usuario autenticado, con soporte para filtrado por estado.

- **Método**: `GET`
- **Ruta**: `/tasks`
- **Autenticación**: **Obligatoria**. Requiere sesión activa en el backend.
- **Query Parameters**:
  - `status` *(opcional)*: Cadena con el estado a filtrar (`pending`, `in_progress`, `completed`). Si se omite, retorna todas las tareas del usuario.

#### Respuestas:
- **`200 OK` (Éxito)**:
  - Si es HTML: Renderiza plantilla `tasks/index.html` con la lista de tareas.
  - Si es JSON:
    ```json
    {
      "status": "success",
      "data": {
        "tasks": [
          {
            "id": 101,
            "title": "Preparar informe mensual",
            "description": "Incluir métricas de rendimiento",
            "status": "pending",
            "due_date": "2026-10-15",
            "created_at": "2026-09-29T14:00:00Z",
            "updated_at": "2026-09-29T14:00:00Z"
          }
        ],
        "count": 1,
        "filter": "pending"
      }
    }
    ```
- **`401 Unauthorized`**: Sesión ausente o inválida.

---

## 2. Creación de Tareas (`HU-01`)

### 2.1. `POST /tasks`
Crea una nueva tarea para el usuario autenticado e inicializa el log de auditoría.

- **Método**: `POST`
- **Ruta**: `/tasks`
- **Autenticación**: **Obligatoria**.
- **Headers**: `Content-Type: application/x-www-form-urlencoded` o `application/json`
- **Payload de Entrada**:
  ```json
  {
    "title": "Revisar arquitectura monolítica",
    "description": "Detallar separación de capas",
    "due_date": "2026-10-05"
  }
  ```
- **Validaciones en Backend**:
  - `title`: Obligatorio, no vacío (`title.strip() != ""`), longitud máxima 150 caracteres.
  - `description`: Opcional.
  - `due_date`: Opcional, formato `YYYY-MM-DD`.
  - `status`: No se acepta en entrada; el backend asigna automáticamente `"pending"`.
- **Efecto colateral**: Emisión de log estructurado y persistencia de `AuditLog` (`action="TASK_CREATED"`).

#### Respuestas:
- **`201 Created` / `302 Found` (Éxito)**:
  - Si es HTML: Redirección a `/tasks`.
  - Si es JSON:
    ```json
    {
      "status": "success",
      "message": "Tarea creada exitosamente",
      "data": {
        "id": 102,
        "title": "Revisar arquitectura monolítica",
        "description": "Detallar separación de capas",
        "status": "pending",
        "due_date": "2026-10-05",
        "created_at": "2026-09-29T15:35:00Z"
      }
    }
    ```
- **`400 Bad Request` (Error de validación)**:
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "El título de la tarea es obligatorio y no puede estar vacío"
  }
  ```
- **`401 Unauthorized`**: Sesión ausente.

---

## 3. Cambio de Estado de Tareas (`HU-03`)

### 3.1. `POST /tasks/<id>/status`
Cambia el estado de una tarea perteneciente al usuario autenticado.

- **Método**: `POST` (o `PATCH`)
- **Ruta**: `/tasks/<int:task_id>/status`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**:
  ```json
  {
    "status": "in_progress"
  }
  ```
- **Transiciones válidas en Backend**:
  - Desde `pending`: hacia `in_progress` o `completed`.
  - Desde `in_progress`: hacia `completed` o `pending`.
  - Desde `completed`: **Bloqueado** (retorna 400).
- **Efecto colateral**: Emisión de log estructurado y registro en `AuditLog` (`action="STATUS_CHANGED"`).

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Estado de tarea actualizado",
    "data": {
      "id": 102,
      "previous_status": "pending",
      "current_status": "in_progress",
      "updated_at": "2026-09-29T15:40:00Z"
    }
  }
  ```
- **`400 Bad Request` (Transición inválida)**:
  ```json
  {
    "status": "error",
    "code": "INVALID_STATE_TRANSITION",
    "message": "No se permite la transición desde 'completed' hacia 'pending' en este incremento (reapertura no implementada)"
  }
  ```
- **`403 Forbidden` / `404 Not Found`**: La tarea no existe o pertenece a otro usuario.
- **`401 Unauthorized`**: Sesión ausente.

---

## 4. Edición de Tareas (`HU-04`)

### 4.1. `POST /tasks/<id>/edit` (o `PUT /tasks/<id>`)
Edita los campos informativos de una tarea existente propia.

- **Método**: `POST` (formulario HTML) o `PUT` (JSON)
- **Ruta**: `/tasks/<int:task_id>/edit`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**:
  ```json
  {
    "title": "Revisar arquitectura monolítica (Actualizado)",
    "description": "Detallar capa de servicios y logging",
    "due_date": "2026-10-10"
  }
  ```
- **Validaciones**:
  - `title`: Obligatorio, no vacío.
  - No altera el `status` (los cambios de estado se gestionan exclusivamente por el endpoint de estado).
- **Efecto colateral**: Emisión de log estructurado y registro en `AuditLog` (`action="TASK_UPDATED"`).

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Tarea actualizada correctamente",
    "data": {
      "id": 102,
      "title": "Revisar arquitectura monolítica (Actualizado)",
      "description": "Detallar capa de servicios y logging",
      "status": "in_progress",
      "due_date": "2026-10-10",
      "updated_at": "2026-09-29T15:45:00Z"
    }
  }
  ```
- **`400 Bad Request`**: Datos inválidos (título vacío).
- **`404 Not Found`**: Tarea inexistente o de otro usuario.
- **`401 Unauthorized`**: Sin sesión activa.
