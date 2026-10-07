# Contrato de Endpoint: Reordenamiento Manual de Tareas (HU-16)

**Blueprint**: `tasks_bp` (`/tasks`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (autorización por creador o asignatario) y Principio V (lote atómico, sin desplazamiento complejo).

> **Nota de alcance**: este es el **único** endpoint nuevo de todo el Incremento 5. HU-15 (completar sin recargar) reutiliza exclusivamente `POST /tasks/<id>/status`, ya documentado en `specs/001-basic-tasks-auth/contracts/task-contracts.md`.

---

## 1. Reordenar Tareas

### 1.1. `POST /tasks/reorder`
Persiste el nuevo orden visual completo tras una operación de arrastrar y soltar.

- **Método**: `POST`
- **Ruta**: `/tasks/reorder`
- **Autenticación**: **Obligatoria**.
- **Headers**: `Content-Type: application/json`, `Accept: application/json`
- **Payload de Entrada**:
  ```json
  {
    "task_ids": [5, 2, 8, 1]
  }
  ```
  El arreglo representa el nuevo orden visual completo, de principio a fin, tal como quedó tras soltar el elemento arrastrado.

#### Respuestas:

- **`200 OK` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Orden actualizado exitosamente",
    "data": {"updated_count": 4}
  }
  ```
- **`400 Bad Request`**: `task_ids` ausente, vacío, o no es un arreglo de enteros.
  ```json
  {"status": "error", "code": "VALIDATION_ERROR", "message": "Debe proporcionar un arreglo de identificadores de tarea"}
  ```
- **`404 Not Found`**: Al menos uno de los `task_ids` no existe, está eliminado lógicamente, o no pertenece al usuario autenticado ni como creador ni como asignatario (Clarifications, Session 2026-10-07, Q3). **La operación completa se rechaza — no se persiste ningún cambio parcial** (ver `research.md` §3 y `plan.md` §4).
  ```json
  {"status": "error", "code": "TASK_NOT_FOUND", "message": "Una o más tareas no existen o no te pertenecen"}
  ```
- **`401 Unauthorized`**: Sin sesión activa.

---

## 2. Extensión del Listado Existente

### 2.1. `GET /tasks?sort=manual`
Nuevo valor del parámetro `sort` ya documentado en `specs/003-task-organization-priority/contracts/task-priority-contracts.md`. Ordena por `manual_order` ascendente. Sin cambios en el resto del contrato de `GET /tasks`.
