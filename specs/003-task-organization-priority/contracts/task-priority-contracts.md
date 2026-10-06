# Contratos de Endpoints: Prioridad, Categorización y Tareas Vencidas (HU-07, HU-08, HU-09)

**Blueprint**: `tasks_bp` (`/tasks`)  
**Cumplimiento**: Principio III (Contrato explícito con campo is_overdue derivado en backend), Principio VII (Autorización) y Principio VIII (Observabilidad).

---

## 1. Listado Extendido de Tareas (`HU-02`, `HU-07`, `HU-08`, `HU-09`)

### 1.1. `GET /tasks`
Retorna el listado de tareas del usuario autenticado soportando filtrado por estado, filtrado por categoría, ordenamiento por prioridad jerárquica y el indicador computado de vencimiento.

- **Método**: `GET`
- **Ruta**: `/tasks`
- **Autenticación**: **Obligatoria**.
- **Query Parameters**:
  - `status` *(opcional)*: `pending` | `in_progress` | `completed`.
  - `category_id` *(opcional)*: ID numérico de la categoría a filtrar, o `none` para tareas sin categoría.
  - `sort` *(opcional)*:
    - `priority_desc`: Ordena por prioridad (alta → media → baja).
    - `priority_asc`: Ordena por prioridad inversa (baja → media → alta).
    - `due_date`: Ordena por fecha límite.
    - `created_at`: Ordena por fecha de creación (por defecto).

#### Respuestas:
- **`200 OK` (JSON)**:
  ```json
  {
    "status": "success",
    "data": {
      "tasks": [
        {
          "id": 101,
          "title": "Entrega final de arquitectura",
          "description": "Especificar e implementar monolito",
          "status": "in_progress",
          "priority": "high",
          "due_date": "2026-09-30",
          "is_overdue": true,
          "category": {
            "id": 2,
            "name": "Universidad",
            "color": "#10B981"
          },
          "created_at": "2026-09-25T10:00:00Z"
        },
        {
          "id": 102,
          "title": "Actualizar documentación del proyecto",
          "description": null,
          "status": "pending",
          "priority": "medium",
          "due_date": "2026-10-15",
          "is_overdue": false,
          "category": null,
          "created_at": "2026-09-28T14:30:00Z"
        }
      ],
      "count": 2,
      "applied_filters": {
        "status": null,
        "category_id": null,
        "sort": "priority_desc"
      }
    }
  }
  ```
- **`401 Unauthorized`**: Sesión ausente o expirada.

---

## 2. Modificación de Prioridad de una Tarea (`HU-07`)

### 2.1. `POST /tasks/<int:task_id>/priority`
Actualiza el nivel de prioridad de una tarea del usuario en cualquier momento de su ciclo de vida activo.

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/priority`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**:
  ```json
  {
    "priority": "high"
  }
  ```

#### Respuestas:
- **`200 OK` / `302 Found`**:
  ```json
  {
    "status": "success",
    "message": "Prioridad actualizada exitosamente",
    "data": {
      "task_id": 101,
      "priority": "high"
    }
  }
  ```
- **`400 Bad Request`**: Valor de prioridad inválido (debe ser `high`, `medium` o `low`) o tarea eliminada.
- **`404 Not Found`**: La tarea no existe o pertenece a otro usuario.

---

## 3. Asignación de Categoría a una Tarea (`HU-08`)

### 3.1. `POST /tasks/<int:task_id>/category`
Asocia una tarea a una categoría existente del usuario, o la desvincula si se envía valor nulo.

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/category`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**:
  ```json
  {
    "category_id": 2
  }
  ```
  *(O `{"category_id": null}` para dejarla sin categoría).*

#### Respuestas:
- **`200 OK` / `302 Found`**:
  ```json
  {
    "status": "success",
    "message": "Categoría asignada correctamente",
    "data": {
      "task_id": 101,
      "category_id": 2
    }
  }
  ```
- **`404 Not Found`**: La tarea o la categoría especificada no existe, o no pertenece al usuario autenticado (prevención de IDOR).
- **`400 Bad Request`**: Tarea eliminada lógicamente.
