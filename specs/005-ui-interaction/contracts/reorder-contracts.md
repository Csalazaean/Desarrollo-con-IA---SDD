# Contratos de Endpoints: Reordenamiento de Tareas (HU-16)

**Blueprint**: `tasks_bp` (`/tasks`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Validación de propiedad en backend) y la restricción de stack (sin framework SPA).

---

## 1. Persistir el Nuevo Orden

### 1.1. `POST /tasks/reorder`

Recibe la lista ordenada de identificadores de tarea y reasigna sus posiciones de forma consecutiva, empezando en 0.

- **Método**: `POST`
- **Ruta**: `/tasks/reorder`
- **Autenticación**: **Obligatoria**.
- **Headers**: `Content-Type: application/json`
- **Payload de Entrada**:
  ```json
  {
    "task_ids": [14, 9, 23, 2]
  }
  ```
  El primer identificador de la lista queda en la posición 0 (más arriba).

#### Respuestas:

- **`200 OK` (Éxito)**:
  ```json
  {
    "status": "success",
    "message": "Orden actualizado exitosamente",
    "data": {
      "reordered_count": 4,
      "ignored_ids": []
    }
  }
  ```
  `ignored_ids` recoge los identificadores que se descartaron por no pertenecer al usuario autenticado, no existir o corresponder a tareas eliminadas lógicamente. La operación **no falla** por ellos: reordena lo que sí es válido e informa de lo que ignoró.

- **`400 Bad Request`**: El campo `task_ids` falta, no es una lista o contiene valores no numéricos.
  ```json
  {
    "status": "error",
    "code": "INVALID_TASK_ORDER",
    "message": "Debe enviar una lista de identificadores de tarea"
  }
  ```

- **`401 Unauthorized`**: Sin sesión activa.

> **Aislamiento (FR-010)**: los identificadores recibidos se filtran contra las tareas del usuario autenticado **antes** de escribir nada. Una petición manipulada que incluya tareas ajenas no altera ni una sola de ellas; se limitan a aparecer en `ignored_ids`.

> **El orden es por usuario**, no global: las posiciones solo se comparan entre tareas del mismo propietario, así que dos personas reordenando en paralelo no interfieren.

---

## 2. Listado con Orden Personal

### 2.1. `GET /tasks` (comportamiento extendido)

El orden **por defecto** del listado pasa a ser el orden personal:

```
ORDER BY position ASC, created_at DESC
```

Los ordenamientos explícitos del Incremento 3 (`sort=priority_desc`, `priority_asc`, `due_date`) **siguen teniendo precedencia** cuando se solicitan, y en ese caso la interfaz **no ofrece** el reordenamiento manual, para no mostrar dos criterios de orden contradictorios (FR-012).

Cada tarea incluye su posición en la respuesta:

```json
{
  "id": 14,
  "title": "Preparar informe",
  "position": 0
}
```

---

## 3. Cambio de Estado sin Recarga (HU-15)

**No se define ningún endpoint nuevo.** La interacción sin recarga consume el endpoint ya existente del Incremento 1:

```
POST /tasks/<int:task_id>/status
Accept: application/json
{ "status": "completed" }
```

Su contrato no cambia. El JavaScript del cliente se limita a invocarlo con `fetch` y a reflejar la respuesta; si responde con error, revierte el cambio visual que había aplicado de forma optimista (FR-003).
