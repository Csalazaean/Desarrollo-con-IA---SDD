# Technical Research: 002-task-closure-recovery

**Feature**: `002-task-closure-recovery`  
**Date**: 2026-10-01  
**Status**: Completed  

---

## 1. Estrategia de Soft Delete en SQLAlchemy y Preservación de Consultas

### Contexto y Problema
La historia `HU-05` requiere que la eliminación de tareas sea lógica y nunca física, asegurando que:
- Las tareas eliminadas no aparezcan en el listado por defecto (`HU-02`).
- Las tareas eliminadas no puedan volver a eliminarse ni editarse (`HU-04`).
- No se rompa ninguna consulta existente del Incremento 1 ni se pierdan los datos o registros de auditoría asociados (Principio VI y VIII).

### Decisiones de Diseño
- **Campos en el modelo `Task`**:
  - `is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)`
  - `deleted_at = db.Column(db.DateTime, nullable=True)`
- **Estrategia en la capa de servicios (`TaskService`)**:
  En lugar de sobrecargar hooks globales de SQLAlchemy (que pueden ocultar comportamiento inesperado en auditoría o migraciones), la exclusión se encapsula explícitamente en `TaskService`:
  - `get_user_tasks(user_id, status=None, include_deleted=False)`: Aplica por defecto `.filter_by(user_id=user_id, is_deleted=False)`.
  - `get_task_by_id(task_id, user_id, include_deleted=False)`: Por defecto busca solo tareas no eliminadas. Si se requiere verificar existencia para responder error específico de "ya eliminada", un método interno o parámetro `include_deleted=True` permite la inspección.
  - `delete_task(task_id, user_id)`:
    - Si la tarea no existe o no pertenece al usuario: lanza `TaskNotFoundError`.
    - Si la tarea tiene `is_deleted == True`: lanza `TaskAlreadyDeletedError` (operación no permitida).
    - Si la tarea está activa: marca `is_deleted = True`, asigna `deleted_at = datetime.now(timezone.utc)`, guarda cambios y emite log `TASK_DELETED`.

### Alternativas Consideradas y Rechazadas
- **Borrado físico (`session.delete(task)`)**: Rechazado tajantemente por violar el requisito funcional de HU-05 y el Principio VI (integridad histórica y persistencia del historial).
- **Filtro global con eventos de ORM (`with_loader_criteria`)**: Rechazado por violar el Principio V (simplicidad sobre generalidad prematura - YAGNI); dificulta consultas de auditoría y análisis forense que requieren acceder a la entidad borrada lógicamente.

---

## 2. Máquina de Estados y Distinción de Reapertura (`TASK_REOPENED`)

### Contexto y Problema
En el Incremento 1, las transiciones válidas eran:
- `pending` → `in_progress`
- `in_progress` → `completed`
- `pending` → `completed`
- `in_progress` → `pending`
La transición directa desde `completed` hacia `pending` estaba deliberadamente bloqueada. La historia `HU-06` requiere habilitar la reapertura exclusivamente desde `completed`, y auditarla de forma distinguible de un `STATUS_CHANGED` estándar.

### Decisiones de Diseño
- **Transición Habilitada**: Únicamente `completed` → `pending`.
- **Diferenciación en Auditoría (`AuditService`)**:
  - Un cambio de estado regular emite `action = "STATUS_CHANGED"` con payload `{ "from": "...", "to": "..." }`.
  - La reapertura emite un evento dedicado `action = "TASK_REOPENED"` con `entity_id = task.id`, `actor_id = user_id`, `timestamp = now_utc()` y detalles estructurados `{ "previous_status": "completed", "new_status": "pending", "trigger": "user_reopen" }`.
- **Restricciones Bloqueantes**:
  - Si `task.status != "completed"`: error `InvalidTaskStateTransitionError` ("Solo se pueden reabrir tareas completadas").
  - Si `task.is_deleted == True`: error `TaskAlreadyDeletedError` ("No se puede reabrir una tarea eliminada").

---

## 3. Modelo y Criptografía de Tokens de Restablecimiento (HU-14)

### Contexto y Problema
La recuperación de contraseña debe:
- Impedir la enumeración de correos registrados (Principio VII).
- No almacenar tokens ni secretos en texto plano (Principio VII).
- Garantizar uso único e invalidación tras expiración.

### Decisiones de Diseño
- **Generación de Token**: Se genera un token criptográfico seguro en memoria usando `secrets.token_urlsafe(32)`.
- **Almacenamiento Seguro (Hash en BD)**:
  El token sin procesar solo se envía al usuario (vía URL de recuperación). En la tabla `password_reset_tokens` únicamente se almacena `hashlib.sha256(token.encode()).hexdigest()`.
  Si la base de datos sufriera una exfiltración o volcado no autorizado, ningún atacante podría utilizar los hashes almacenados para restablecer cuentas.
- **Ciclo de Vida y Expiración**:
  - Vida útil: 30 minutos desde su generación (`expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)`).
  - Estado de uso: Columna `used_at = db.Column(db.DateTime, nullable=True)`.
  - Un token es válido si `token_record.used_at is None` y `datetime.now(timezone.utc) < token_record.expires_at`.
  - Invalidación atómica: En la misma transacción donde se actualiza `user.password_hash`, se fija `token_record.used_at = datetime.now(timezone.utc)`.
- **Mitigación de Enumeración de Cuentas**:
  El endpoint `POST /auth/forgot-password` retorna exactamente la misma respuesta HTTP `200 OK` con el mensaje:
  *"Si el correo ingresado coincide con una cuenta activa en el sistema, recibirás un correo con las instrucciones para restablecer tu contraseña."*
  Tanto si el correo existe como si no existe en la base de datos, el flujo HTTP concluye idénticamente sin filtrar discrepancias.

---

## 4. Estrategia de Envío de Correo en Entorno de Desarrollo

### Decisión
**Simulación en consola y registro en el logger de la aplicación Flask (`app.logger.info`)**, sin integración de servicios SMTP externos de terceros (SendGrid, Mailgun, Amazon SES).

### Justificación Técnica y Académica
1. **Principio I (Monolito por diseño)**: Evita atar el monolito a servicios SaaS externos de mensajería o dependencias de red externas que impiden levantar el entorno de desarrollo y pruebas de manera autónoma con un solo comando (`run.ps1` o `pytest`).
2. **Principio V (Simplicidad sobre generalidad prematura - YAGNI)**: Integrar un proveedor SMTP real en una etapa académica temprana introduce manejo de credenciales de terceros, costos, cuotas de envío, configuración de SPF/DKIM y potenciales fallos de red ajenos al código a evaluar.
3. **Principio VII (Seguridad por defecto)**: Evita commitear claves de API o credenciales SMTP en el repositorio o exponer cuentas personales de los desarrolladores.
4. **Flujo de desarrollo y pruebas**: Al imprimir el enlace de restablecimiento con su token en la consola/log del servidor (`http://localhost:5000/auth/reset-password/<token>`), los desarrolladores y evaluadores pueden probar el flujo completo de recuperación E2E de forma inmediata, predecible y reproducible sin conexión a internet ni bandejas de entrada reales.
