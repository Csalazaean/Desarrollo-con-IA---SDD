# Contratos de Endpoints: Asignación de Tareas (HU-10)

**Blueprint**: `tasks_bp` (`/tasks`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Validación del destinatario en backend y autorización del creador) y Principio VIII (Observabilidad).

---

## 1. Asignar o Reasignar una Tarea

### 1.1. `POST /tasks/<int:task_id>/assign`

Asigna una tarea a un usuario registrado indicando su correo electrónico. Enviar el campo vacío retira la asignación.

- **Método**: `POST`
- **Ruta**: `/tasks/<int:task_id>/assign`
- **Autenticación**: **Obligatoria**. Solo el **creador** de la tarea puede asignarla.
- **Payload de Entrada**:
  ```json
  {
    "assignee_email": "companero@ejemplo.com"
  }
  ```
  *(O `{"assignee_email": ""}` para desasignar.)*

#### Respuestas:

- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Tarea asignada exitosamente",
    "data": {
      "task_id": 101,
      "assigned_to_id": 7,
      "assignee_email": "companero@ejemplo.com",
      "notification_created": true
    }
  }
  ```
  `notification_created` es `false` cuando el creador se autoasigna la tarea o cuando se retira la asignación.

- **`400 Bad Request`**: El correo indicado **no corresponde a ningún usuario registrado**, o la tarea está eliminada lógicamente.
  ```json
  {
    "status": "error",
    "code": "ASSIGNEE_NOT_FOUND",
    "message": "No existe un usuario registrado con el correo 'companero@ejemplo.com'"
  }
  ```

- **`403 Forbidden`**: El usuario autenticado existe y la tarea también, pero **no es su creador**.
  ```json
  {
    "status": "error",
    "code": "NOT_TASK_OWNER",
    "message": "Solo el creador de la tarea puede asignarla"
  }
  ```

- **`404 Not Found`**: La tarea no existe.
- **`401 Unauthorized`**: Sin sesión activa.

> **403 frente a 404**: se distinguen deliberadamente porque el escenario 5 de la Historia 1 lo exige. La tarea pertenece a otro usuario pero su existencia no es un secreto del sistema: lo que se niega es el permiso, no la existencia.

---

## 2. Listado de Tareas con Filtro por Autoría

### 2.1. `GET /tasks`

Se extiende el listado ya existente para incluir las tareas asignadas al usuario autenticado, además de las que creó.

- **Query Parameters (nuevo)**:
  - `scope` *(opcional)*:
    - `all` *(por defecto)*: tareas creadas por el usuario **más** las asignadas a él.
    - `created`: solo las que creó.
    - `assigned`: solo las que le fueron asignadas por otra persona.

Los parámetros `status`, `category_id` y `sort` del Incremento 3 siguen funcionando y se combinan con `scope`.

#### Respuesta `200 OK` (campos nuevos por tarea):
```json
{
  "id": 101,
  "title": "Preparar informe",
  "creator_email": "ana@ejemplo.com",
  "assigned_to_id": 7,
  "assignee_email": "companero@ejemplo.com",
  "is_mine": true,
  "is_assigned_to_me": false
}
```

`is_mine` e `is_assigned_to_me` los resuelve el backend respecto del usuario autenticado, para que la plantilla solo pinte el distintivo y no deduzca autoría por su cuenta.
