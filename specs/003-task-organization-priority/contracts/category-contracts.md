# Contratos de Endpoints: Gestión de Categorías (HU-08)

**Blueprint**: `categories_bp` (`/categories`)  
**Cumplimiento**: Principio II (Separación de capas para la nueva entidad Category), Principio III (Contrato explícito), Principio VII (Verificación de sesión) y Principio VIII (Observabilidad).

---

## 1. Listado de Categorías

### 1.1. `GET /categories`
Retorna las categorías creadas por el usuario autenticado junto con el conteo de tareas activas asociadas.

- **Método**: `GET`
- **Ruta**: `/categories`
- **Autenticación**: **Obligatoria** (sesión activa).
- **Headers**: `Accept: application/json` o `text/html`

#### Respuestas:
- **`200 OK` (JSON)**:
  ```json
  {
    "status": "success",
    "data": {
      "categories": [
        {
          "id": 1,
          "name": "Trabajo",
          "description": "Proyectos de la oficina",
          "color": "#3B82F6",
          "task_count": 4,
          "created_at": "2026-10-01T16:00:00Z"
        }
      ]
    }
  }
  ```
- **`401 Unauthorized`**: Sesión ausente o expirada.

---

## 2. Creación de Categoría

### 2.1. `POST /categories`
Crea una nueva categoría para el usuario autenticado. Registra auditoría `CATEGORY_CREATED`.

- **Método**: `POST`
- **Ruta**: `/categories`
- **Autenticación**: **Obligatoria**.
- **Headers**: `Content-Type: application/json` o `application/x-www-form-urlencoded`
- **Payload de Entrada**:
  ```json
  {
    "name": "Universidad",
    "description": "Entregas académicas y parciales",
    "color": "#10B981"
  }
  ```

#### Respuestas:
- **`201 Created` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Categoría creada exitosamente",
    "data": {
      "id": 2,
      "name": "Universidad",
      "color": "#10B981"
    }
  }
  ```
- **`400 Bad Request`**: Nombre vacío, longitud mayor a 50 caracteres o nombre duplicado para este usuario.
  ```json
  {
    "status": "error",
    "code": "DUPLICATE_CATEGORY_NAME",
    "message": "Ya tienes una categoría registrada con el nombre 'Universidad'"
  }
  ```
- **`400 Bad Request`**: `color` no cumple el formato hexadecimal estricto `#RRGGBB` (ver spec Clarifications, Session 2026-10-06, Q3).
  ```json
  {
    "status": "error",
    "code": "INVALID_CATEGORY_COLOR",
    "message": "El color debe tener el formato hexadecimal #RRGGBB"
  }
  ```
- **`401 Unauthorized`**: Sin sesión activa.

---

## 3. Edición de Categoría

> Agregado tras `/speckit-analyze` (hallazgo E1): FR-007 de la spec exige "editar" categorías, pero este contrato no lo cubría.

### 3.1. `POST /categories/<int:category_id>/edit`
Edita nombre, descripción y/o color de una categoría propia. Reutiliza las mismas validaciones que la creación (unicidad de nombre excluyendo la propia categoría, formato de color).

- **Método**: `POST`
- **Ruta**: `/categories/<int:category_id>/edit`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**:
  ```json
  {
    "name": "Universidad",
    "description": "Entregas académicas y parciales",
    "color": "#10B981"
  }
  ```

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Categoría actualizada exitosamente",
    "data": {
      "id": 2,
      "name": "Universidad",
      "color": "#10B981"
    }
  }
  ```
- **`400 Bad Request`**: Nombre duplicado (excluyendo la propia categoría) o `color` con formato inválido.
  ```json
  {
    "status": "error",
    "code": "DUPLICATE_CATEGORY_NAME",
    "message": "Ya tienes una categoría registrada con el nombre 'Universidad'"
  }
  ```
- **`404 Not Found`**: La categoría no existe o pertenece a otro usuario.
- **`401 Unauthorized`**: Sin sesión activa.

---

## 4. Eliminación de Categoría (Desvinculación sin Cascada)

### 4.1. `POST /categories/<int:category_id>/delete` (o `DELETE /categories/<int:category_id>`)
Elimina la categoría del usuario y desvincula automáticamente todas las tareas asociadas (`category_id = NULL`), sin borrar ninguna tarea.

- **Método**: `POST` / `DELETE`
- **Ruta**: `/categories/<int:category_id>/delete`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK` / `302 Found` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Categoría eliminada exitosamente. Las tareas asociadas permanecen sin categoría.",
    "data": {
      "deleted_category_id": 2,
      "tasks_unlinked_count": 5
    }
  }
  ```
- **`404 Not Found`**: La categoría no existe o pertenece a otro usuario.
- **`401 Unauthorized`**: Sin sesión.
