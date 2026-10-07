# Contratos de Endpoints: Notificaciones Internas (HU-11)

**Blueprint**: `notifications_bp` (`/notifications`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Aislamiento estricto por usuario) y Principio IX del alcance: las notificaciones viven **solo** dentro de la aplicación, sin correo ni push externo (FR-009).

---

## 1. Centro de Notificaciones

### 1.1. `GET /notifications`

Lista las notificaciones del usuario autenticado en orden cronológico descendente (FR-010).

- **Método**: `GET`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK` (JSON)**:
  ```json
  {
    "status": "success",
    "data": {
      "notifications": [
        {
          "id": 12,
          "message": "ana@ejemplo.com te asignó la tarea 'Preparar informe'",
          "task_id": 101,
          "sender_id": 3,
          "is_read": false,
          "read_at": null,
          "created_at": "2026-10-06T22:10:00Z"
        }
      ],
      "unread_count": 1
    }
  }
  ```
- **`401 Unauthorized`**: Sin sesión activa.

> Un usuario **nunca** ve notificaciones de terceros: la consulta filtra siempre por `recipient_id` igual al usuario de la sesión (FR-014).

---

## 2. Marcar una Notificación como Leída

### 2.1. `POST /notifications/<int:notification_id>/read`

- **Método**: `POST`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK` / `302 Found`**:
  ```json
  {
    "status": "success",
    "message": "Notificación marcada como leída",
    "data": {
      "id": 12,
      "is_read": true,
      "read_at": "2026-10-06T22:15:00Z",
      "unread_count": 0
    }
  }
  ```
- **`404 Not Found`**: La notificación no existe **o pertenece a otro usuario**. Se responde lo mismo en ambos casos para no confirmar la existencia de notificaciones ajenas.
- **`401 Unauthorized`**: Sin sesión activa.

> **Idempotencia**: marcar como leída una notificación ya leída responde `200 OK` y **conserva el `read_at` original**. Dos pestañas marcando a la vez no producen inconsistencias en el contador (Edge Case de concurrencia).

> **Persistencia**: la notificación **no se elimina** al leerse; permanece en el historial (FR-013).

---

## 3. Marcar Todas como Leídas

### 3.1. `POST /notifications/read-all`

Marca como leídas, de forma atómica, todas las notificaciones pendientes del usuario autenticado (FR-012).

- **Método**: `POST`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK` / `302 Found`**:
  ```json
  {
    "status": "success",
    "message": "Todas las notificaciones fueron marcadas como leídas",
    "data": {
      "marked_count": 4,
      "unread_count": 0
    }
  }
  ```
- **`401 Unauthorized`**: Sin sesión activa.

---

## 4. Contador en la Interfaz

El contador de no leídas (FR-011) se expone a todas las plantillas mediante un **context processor**, de modo que la barra de navegación lo muestre en cualquier página sin que cada ruta tenga que calcularlo y pasarlo. Para usuarios sin sesión el valor es `0`.
