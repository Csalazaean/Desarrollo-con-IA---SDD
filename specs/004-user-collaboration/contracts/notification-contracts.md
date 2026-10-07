# Contratos de Endpoints: Notificaciones Internas (HU-11)

**Blueprint**: `notifications_bp` (`/notifications`)
**Cumplimiento**: Principio III (Contrato explícito), Principio VII (Aislamiento estricto por destinatario) y Principio V (sin servicios externos de mensajería, FR-009).

---

## 1. Listado de Notificaciones

### 1.1. `GET /notifications`
Retorna las notificaciones del usuario autenticado, ordenadas cronológicamente descendente (FR-010), junto con el conteo de no leídas.

- **Método**: `GET`
- **Ruta**: `/notifications`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK` (JSON)**:
  ```json
  {
    "status": "success",
    "data": {
      "notifications": [
        {
          "id": 5,
          "message": "companero@ejemplo.com te asignó la tarea 'Preparar informe'",
          "task_id": 101,
          "is_read": false,
          "created_at": "2026-10-06T22:00:00Z",
          "read_at": null
        }
      ],
      "unread_count": 1
    }
  }
  ```
- **`401 Unauthorized`**: Sesión ausente o expirada.

---

## 2. Marcar Notificación Individual como Leída

### 2.1. `POST /notifications/<int:notification_id>/read`
Marca una notificación propia como leída. Operación idempotente (Edge Case "Concurrencia en marcado de lectura").

- **Método**: `POST`
- **Ruta**: `/notifications/<int:notification_id>/read`
- **Autenticación**: **Obligatoria**.

#### Respuestas:
- **`200 OK`**:
  ```json
  {"status": "success", "message": "Notificación marcada como leída", "data": {"id": 5, "is_read": true}}
  ```
- **`404 Not Found`**: La notificación no existe o no pertenece al usuario autenticado (nunca revela si existe para otro usuario, FR-014).
- **`401 Unauthorized`**: Sin sesión activa.

---

## 3. Marcar Todas como Leídas

### 3.1. `POST /notifications/mark-all-read`
Marca todas las notificaciones pendientes del usuario autenticado como leídas, de forma atómica (FR-012).

- **Método**: `POST`
- **Ruta**: `/notifications/mark-all-read`
- **Autenticación**: **Obligatoria**.
- **Payload de Entrada**: Vacío.

#### Respuestas:
- **`200 OK`**:
  ```json
  {"status": "success", "message": "Todas las notificaciones fueron marcadas como leídas", "data": {"updated_count": 3}}
  ```
- **`401 Unauthorized`**: Sin sesión activa.
