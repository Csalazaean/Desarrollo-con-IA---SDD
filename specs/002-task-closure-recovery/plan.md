# Implementation Plan: 002-task-closure-recovery

**Branch**: `002-task-closure-recovery` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-task-closure-recovery/spec.md`

---

## Summary

Implementar el segundo incremento funcional del monolito **TaskControl**:
1. **Eliminación lógica de tareas (`HU-05`)**: soporte de *soft delete* en `Task` con exclusión transparente en consultas preexistentes, sin borrado físico ni pérdida del historial de auditoría.
2. **Reapertura de tareas completadas (`HU-06`)**: habilitación de la transición `completed` → `pending` auditada formalmente con el evento diferenciado `TASK_REOPENED`.
3. **Recuperación segura de contraseña (`HU-14`)**: flujo de solicitud neutro (sin enumeración de cuentas), generación y almacenamiento hasheado de tokens temporales de uso único con expiración de 30 minutos, e invalidación atómica al cambiar la clave.

Todo el diseño se apoya en los cimientos del Incremento 1 (Flask 3.x, SQLAlchemy, Flask-Migrate, Werkzeug, Jinja2 y vanilla JavaScript), manteniendo la arquitectura en 4 capas estrictas, enfoque *test-first* bloqueante en servicios y total apego a la constitución del proyecto.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, Flask-SQLAlchemy, Flask-Migrate (Alembic), Werkzeug (security)  
**Storage**: Base de datos relacional SQLite (desarrollo/pruebas) / compatible con PostgreSQL  
**Testing**: pytest (pytest-flask)  
**Target Platform**: Linux / Windows / macOS server (proceso monolítico único)  
**Project Type**: Monolito web (Jinja2 en servidor + Fetch API vanilla en cliente)  
**Performance Goals**: Tiempo de respuesta < 50ms para consultas filtradas con soft delete; < 150ms para hash criptográfico de token y contraseña  
**Constraints**:
- Arquitectura monolítica pura sin microservicios ni brokers asíncronos (Principio I).
- Separación estricta en 4 capas sin llamadas cruzadas (Principio II).
- Contratos explícitos para cada endpoint HTTP nuevo (Principio III).
- Desarrollo guiado por pruebas (*Test-first*) bloqueante en servicios de dominio (Principio IV).
- Principio YAGNI: sin proveedores externos de correo en desarrollo (Principio V).
- Migraciones de esquema versionadas con Alembic garantizando compatibilidad retrospectiva (Principio VI).
- Seguridad por defecto: tokens hasheados, no enumeración de correos, sin secretos en texto plano (Principio VII).
- Observabilidad estructurada: emisión de `TASK_DELETED`, `TASK_REOPENED`, `PASSWORD_RESET_REQUESTED` y `PASSWORD_RESET_COMPLETED` (Principio VIII).  
**Scale/Scope**: 3 Historias de Usuario (HU-05, HU-06, HU-14)  

---

## Constitution Check

*GATE: Evaluado antes del diseño y re-verificado tras la definición técnica.*

| Principio Constitucional | Estado | Justificación y Mecanismo de Cumplimiento |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Mismo repositorio, mismo proceso Flask y misma base de datos relacional. La entrega de tokens de recuperación no utiliza colas asíncronas externas (RabbitMQ/Celery) ni servicios serverless. |
| **II. Separación de responsabilidades** | **PASS** | `models/` (esquema y tipos) → `services/` (lógica de soft delete, validación de estado, hashing y expiración de tokens) → `routes/` (blueprints `tasks.py` y `auth.py`) → `templates/` (vistas Jinja2). Las rutas no consultan ORM directo. |
| **III. Contrato explícito** | **PASS** | Formalizados en `contracts/task-contracts.md` y `contracts/auth-contracts.md` con rutas, métodos, payloads y códigos de error normalizados. |
| **IV. Test-first en lógica de negocio** | **PASS** | Reglas de soft delete, no re-eliminación, máquina de estados y expiración/uso único de tokens se especifican en pruebas automatizadas bloqueantes antes del código funcional. |
| **V. Simplicidad sobre generalidad (YAGNI)** | **PASS** | Envío de correos simulado por log en desarrollo, evitando SDKs o SaaS de terceros; manejo de tokens mediante SHA-256 directo sobre modelo relacional. |
| **VI. Integridad de datos y migraciones** | **PASS** | Soft delete preserva físicamente filas y relaciones foráneas. Columnas nuevas (`is_deleted`, `deleted_at`) y tabla `password_reset_tokens` se incorporan mediante migración versionada con Alembic. |
| **VII. Seguridad por defecto** | **PASS** | Tokens temporales almacenados exclusivamente como hash SHA-256; respuesta neutra ante solicitudes de recuperación (prevención de enumeración de usuarios); secretos en `.env`. |
| **VIII. Observabilidad mínima viable** | **PASS** | Emisión obligatoria de logs estructurados con `actor_id`, `action`, `entity_id` y `timestamp` para `TASK_DELETED`, `TASK_REOPENED`, `PASSWORD_RESET_REQUESTED` y `PASSWORD_RESET_COMPLETED`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-task-closure-recovery/
├── spec.md              # Especificación funcional validada
├── plan.md              # Este plan de implementación técnica
├── research.md          # Investigación técnica y decisiones arquitectónicas (Fase 0)
├── data-model.md        # Esquema de datos, ERD y máquina de estados ampliada (Fase 1)
├── quickstart.md        # Guía de inicialización, migraciones y pruebas E2E (Fase 1)
├── contracts/           # Contratos explícitos de endpoints HTTP (Fase 1)
│   ├── task-contracts.md
│   └── auth-contracts.md
└── checklists/
    └── requirements.md  # Checklist de calidad de especificación
```

### Source Code Impact

```text
src/
└── taskcontrol/
    ├── models/
    │   ├── task.py               # Incorporación de is_deleted y deleted_at
    │   ├── password_reset.py     # Nuevo modelo PasswordResetToken
    │   └── audit.py              # Nuevas constantes de acciones de auditoría
    ├── services/
    │   ├── task_service.py       # Métodos delete_task(), reopen_task(), filtro is_deleted en listado
    │   ├── user_service.py       # Métodos request_password_reset(), verify_reset_token(), reset_password()
    │   └── audit_service.py      # Soporte para registrar los 4 nuevos eventos de auditoría
    ├── routes/
    │   ├── tasks.py              # Endpoints POST /tasks/<id>/delete y POST /tasks/<id>/reopen
    │   └── auth.py               # Endpoints /auth/forgot-password y /auth/reset-password/<token>
    ├── templates/
    │   ├── auth/
    │   │   ├── forgot_password.html  # Formulario de solicitud de recuperación
    │   │   └── reset_password.html   # Formulario de ingreso de nueva contraseña
    │   └── tasks/
    │       └── index.html            # Acciones añadidas: botón Eliminar y botón Reabrir
    └── static/
        └── js/
            └── main.js               # Soporte opcional para confirmación de eliminación/reapertura

tests/
├── services/
│   ├── test_task_service.py      # Pruebas bloqueantes de soft delete, no re-eliminación y reapertura
│   └── test_user_service.py      # Pruebas bloqueantes de tokens (hash, expiración, uso único, no enumeración)
└── functional/
    ├── test_task_routes.py       # Pruebas HTTP para endpoints /delete y /reopen
    └── test_auth_routes.py       # Pruebas HTTP para endpoints /forgot-password y /reset-password

migrations/versions/
└── xxxx_add_soft_delete_and_password_reset.py  # Script de migración reproducible Alembic
```

---

## Detalle Técnico de los Puntos del Incremento

### 1. Extensión del Modelo `Task` para Soft Delete sin Romper Consultas Preexistentes

- **Campos en `src/taskcontrol/models/task.py`**:
  ```python
  is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
  deleted_at = db.Column(db.DateTime, nullable=True)
  ```
- **Preservación de consultas existentes (`TaskService`)**:
  - `TaskService.get_user_tasks(user_id, status=None, include_deleted=False)`:
    Por defecto, añade la condición `.filter_by(user_id=user_id, is_deleted=False)`. Las consultas del Incremento 1 (`HU-02`) continúan retornando únicamente tareas activas sin requerir cambios en su firma o invocación.
  - `TaskService.get_task_by_id(task_id, user_id, include_deleted=False)`:
    Filtra por defecto `is_deleted=False`. Si un usuario intenta ver o editar una tarea eliminada lógicamente, el método arroja `TaskNotFoundError`, garantizando que la tarea quede inaccesible en operaciones habituales.
  - Al ejecutar `delete_task(task_id, user_id)`:
    - Se busca la tarea (incluyendo eliminadas para diagnosticar).
    - Si no existe o `task.user_id != user_id`: arroja `TaskNotFoundError`.
    - Si `task.is_deleted is True`: arroja `TaskAlreadyDeletedError` (rechazo controlado sin doble auditoría).
    - Si está activa: fija `task.is_deleted = True`, `task.deleted_at = datetime.now(timezone.utc)`, persiste y audita `TASK_DELETED`.

---

### 2. Distinción de Reapertura en Auditoría y Máquina de Estados

- **Diferenciación en el Log de Auditoría (`AuditLog`)**:
  - Cambio ordinario (`HU-03`): `action = "STATUS_CHANGED"` con detalle `{"from": "pending", "to": "in_progress"}`.
  - Reapertura (`HU-06`): `action = "TASK_REOPENED"` con detalle estructurado `{"previous_status": "completed", "new_status": "pending", "trigger": "user_reopen"}`.
  Esto permite consultar analíticamente cuántas tareas fueron reabiertas versus cuántas sufrieron transiciones normales de trabajo.
- **Transición Habilitada en la Máquina de Estados**:
  - Transición autorizada: `completed` → `pending`.
  - Se implementa el método `TaskService.reopen_task(task_id, user_id)`.
  - Si `task.status != "completed"`: rechaza con `InvalidTaskStateTransitionError` ("Solo se pueden reabrir tareas completadas").
  - Si `task.is_deleted is True`: rechaza con `TaskAlreadyDeletedError` ("No se puede reabrir una tarea eliminada").

---

### 3. Contratos de Nuevos Endpoints HTTP

#### A. Eliminación Lógica de Tarea
- **Ruta y Método**: `POST /tasks/<int:task_id>/delete` (y soporte `DELETE /tasks/<int:task_id>`).
- **Autenticación**: Sesión activa requerida (decorador `@login_required`).
- **Payload Entrada**: Vacío (o CSRF token en form HTML).
- **Payload Salida (JSON)**:
  `{"status": "success", "message": "Tarea eliminada exitosamente", "data": {"task_id": 101, "is_deleted": true}}`
  (En HTML: redirección `302 /tasks` con flash message).
- **Códigos HTTP**:
  - `200 OK` / `302 Found`: Eliminación exitosa.
  - `401 Unauthorized`: Sin sesión.
  - `404 Not Found`: Tarea inexistente o de otro usuario.
  - `400 Bad Request` / `409 Conflict`: Tarea ya eliminada previamente.

#### B. Reapertura de Tarea
- **Ruta y Método**: `POST /tasks/<int:task_id>/reopen`.
- **Autenticación**: Sesión activa requerida.
- **Payload Entrada**: Vacío.
- **Payload Salida (JSON)**:
  `{"status": "success", "message": "Tarea reabierta exitosamente", "data": {"task_id": 101, "status": "pending"}}`
  (En HTML: redirección `302 /tasks`).
- **Códigos HTTP**:
  - `200 OK` / `302 Found`: Reapertura exitosa.
  - `401 Unauthorized`: Sin sesión.
  - `404 Not Found`: Tarea no encontrada o ajena.
  - `400 Bad Request`: Tarea no está en estado `completed` o está eliminada.

#### C. Solicitud de Restablecimiento de Contraseña
- **Ruta y Método**: `POST /auth/forgot-password`.
- **Autenticación**: Pública.
- **Payload Entrada**: `{"email": "usuario@ejemplo.com"}` (o campo `email` en form).
- **Payload Salida**:
  `{"status": "success", "message": "Si el correo ingresado coincide con una cuenta activa en el sistema, recibirás un correo con las instrucciones para restablecer tu contraseña."}`
- **Códigos HTTP**:
  - `200 OK`: Siempre que el formato de email sea válido (respuesta neutra tanto si existe como si no existe).
  - `400 Bad Request`: Formato de correo inválido o campo vacío.

#### D. Confirmación de Restablecimiento con Token
- **Rutas y Métodos**:
  - `GET /auth/reset-password/<string:token>`: Valida token y renderiza formulario. Retorna `200 OK` o `400 Bad Request` si el token expiró/ya se usó.
  - `POST /auth/reset-password/<string:token>`: Procesa la nueva clave.
- **Payload Entrada (POST)**:
  `{"new_password": "NuevaPassword123!", "confirm_password": "NuevaPassword123!"}`
- **Payload Salida (POST)**:
  `{"status": "success", "message": "Tu contraseña ha sido restablecida exitosamente."}` (o redirección `302 /auth/login`).
- **Códigos HTTP**:
  - `200 OK` / `302 Found`: Contraseña actualizada y token invalidado.
  - `400 Bad Request`: Token inválido/expirado/consumido o contraseñas no coinciden / longitud menor a 8 caracteres.

---

### 4. Modelo de Datos y Estrategia de Expiración de Tokens

- **Modelo `PasswordResetToken`**:
  ```python
  class PasswordResetToken(db.Model):
      __tablename__ = 'password_reset_tokens'
      id = db.Column(db.Integer, primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
      token_hash = db.Column(db.String(64), nullable=False, index=True)
      expires_at = db.Column(db.DateTime, nullable=False)
      used_at = db.Column(db.DateTime, nullable=True)
      created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
  ```
- **Protección Criptográfica**:
  - Se genera un token aleatorio con `secrets.token_urlsafe(32)`.
  - En la base de datos se guarda exclusivamente `hashlib.sha256(raw_token.encode('utf-8')).hexdigest()`.
  - Cero secretos en texto plano en la base de datos (Principio VII).
- **Vida Útil y Expiración**:
  - `expires_at = now_utc + timedelta(minutes=30)`.
  - Al buscar el token por `token_hash`:
    `token_record = PasswordResetToken.query.filter_by(token_hash=h, used_at=None).first()`
    Si `token_record is None` o `token_record.expires_at < now_utc`: token inválido/expirado.
- **Invalidación Atómica tras Uso**:
  En la misma transacción que actualiza `user.password_hash`, se fija `token_record.used_at = now_utc`.
- **Prevención de Enumeración de Cuentas**:
  - `UserService.request_password_reset(email)`:
    - Normaliza email a minúsculas y valida formato.
    - Consulta usuario: `user = User.query.filter_by(email=email).first()`.
    - Si `user is None`: no genera token, no lanza error y retorna inmediatamente `True`.
    - Si `user` existe: invalida tokens pendientes previos del usuario, genera nuevo token, guarda su hash en BD, emite evento de simulación y retorna `True`.
    - La capa HTTP entrega siempre el mismo mensaje neutro e idéntico código `200 OK`.

---

### 5. Estrategia de Envío de Correo en Desarrollo y Justificación

- **Mecanismo Adoptado**: **Simulación mediante registro estructurado en la consola y logger de Flask (`app.logger.info`)**, prescindiendo de servicios SMTP externos de terceros.
- **Justificación**:
  1. **Principio I (Monolito por diseño)**: Mantiene el monolito 100% autocontenido y autónomo. No requiere servicios serverless, colas externas (Celery) ni pasarelas SMTP dependientes de conexión a internet.
  2. **Principio V (Simplicidad sobre generalidad - YAGNI)**: En un entorno de desarrollo y evaluación académica, integrar proveedores de pago (SendGrid, Mailgun) introduce sobreingeniería, riesgos de cuotas, demoras por spam y configuración compleja de DNS (SPF/DKIM).
  3. **Principio VII (Seguridad por defecto)**: Evita filtrar contraseñas o claves de API en repositorios Git y elude el uso de correos personales de los estudiantes.
  4. **Facilidad de Verificación y Testing E2E**: El enlace directo con el token (`http://localhost:5000/auth/reset-password/<token>`) se imprime de inmediato en la consola de ejecución de Flask, permitiendo probar y evaluar el flujo en segundos de forma reproducible.

---

### 6. Migraciones sobre el Esquema Existente (Principio VI)

- **Comando de Generación**:
  ```powershell
  flask db migrate -m "add_soft_delete_to_task_and_password_reset_token"
  ```
- **Operaciones Alembic (`upgrade`)**:
  1. `op.add_column('tasks', sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False))`
  2. `op.add_column('tasks', sa.Column('deleted_at', sa.DateTime(), nullable=True))`
  3. `op.create_index(op.f('ix_tasks_is_deleted'), 'tasks', ['is_deleted'], unique=False)`
  4. `op.create_table('password_reset_tokens', ...)` con clave foránea referenciando `users.id` e índice en `token_hash`.
- **Compatibilidad Retrospectiva**:
  El `server_default='0'` garantiza que todas las tareas creadas previamente durante el Incremento 1 permanezcan activas con `is_deleted = False` sin requerir scripts manuales ni causar inconsistencias. La función `downgrade()` retira de forma ordenada la tabla y las columnas nuevas.

---

### 7. Pruebas Automatizadas Bloqueantes a Nivel de Modelo/Servicio (Principio IV)

Siguiendo el ciclo estricto *Test-First*, las siguientes pruebas unitarias y de servicio son obligatorias y bloqueantes antes de dar por finalizado el incremento:

1. **`test_soft_delete_task_marks_deleted_and_sets_timestamp`**:
   Verifica que llamar a `TaskService.delete_task` establece `is_deleted = True` y fija `deleted_at` con fecha UTC.
2. **`test_soft_delete_preserves_task_in_database_and_audit_history`**:
   Verifica que la tarea continúa existiendo en la tabla `tasks` (comprobando por ID directo en sesión SQL) y que todos los logs históricos en `audit_logs` siguen asociados a `entity_id`.
3. **`test_deleted_task_excluded_from_default_listing`**:
   Crea 3 tareas, elimina 1 y verifica que `TaskService.get_user_tasks` retorne únicamente las 2 tareas activas.
4. **`test_cannot_delete_already_deleted_task`**:
   Llama a `delete_task` sobre una tarea previamente eliminada y comprueba que se arroje de manera controlada `TaskAlreadyDeletedError`.
5. **`test_cannot_edit_deleted_task`**:
   Verifica que intentar invocar `TaskService.update_task` sobre una tarea con `is_deleted = True` lance excepción bloqueante.
6. **`test_reopen_completed_task_success`**:
   Verifica que reabrir una tarea en estado `completed` cambie su estado a `pending`.
7. **`test_reopen_task_generates_specific_task_reopened_audit_log`**:
   Comprueba que en `audit_logs` se registre la acción explícita `TASK_REOPENED` con el detalle de la transición anterior y nueva.
8. **`test_cannot_reopen_non_completed_or_deleted_task`**:
   Comprueba que intentar reabrir una tarea en estado `pending`, `in_progress` o `is_deleted = True` sea rechazado con `InvalidTaskStateTransitionError` o `TaskAlreadyDeletedError`.
9. **`test_password_reset_request_neutral_response_existing_and_non_existing_email`**:
   Invoca la solicitud con correo registrado y con correo inexistente, verificando que ambos retornen `True` sin revelar la existencia del usuario.
10. **`test_password_reset_token_hashed_in_database`**:
    Verifica que en `password_reset_tokens.token_hash` se almacene el resumen SHA-256 de 64 caracteres hexadecimales y en ningún caso el token sin procesar.
11. **`test_password_reset_success_updates_password_and_invalidates_token`**:
    Realiza el cambio de clave y verifica que la contraseña cambie, que el nuevo login funcione y que `used_at` quede registrado en la base de datos.
12. **`test_cannot_reuse_already_used_reset_token`**:
    Intenta ejecutar un segundo restablecimiento con el mismo token y verifica que sea rechazado.
13. **`test_cannot_use_expired_reset_token`**:
    Simula un token cuya fecha `expires_at` se encuentra en el pasado y verifica que el sistema lo rechace como inválido/expirado.
