# Research & Decisions: 001-basic-tasks-auth

**Feature**: 001-basic-tasks-auth (Gestión básica de tareas con autenticación)  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Arquitectura y Estructura de Capas del Monolito (Principio I y II)

### Decisión
Estructurar el monolito en una única aplicación empaquetada en Python bajo el directorio `src/taskcontrol/` utilizando el patrón de fábrica de aplicaciones de Flask (`create_app`), separando estrictamente las responsabilidades en cuatro capas jerárquicas:
1. `models/`: Definición de tablas y entidades SQLAlchemy puras.
2. `services/`: Lógica de negocio agnóstica de HTTP (validaciones de dominio, ciclo de vida de tareas, cálculo de transiciones, invocación del logger de auditoría).
3. `routes/`: Blueprints de Flask (`auth.py`, `tasks.py`, `main.py`) que solo manejan solicitudes HTTP, validación de formularios/payloads y delegación inmediata a la capa de servicios.
4. `templates/` y `static/`: Vistas Jinja2 y archivos JavaScript vanilla sin framework SPA.

### Razón de ser
- Cumple fielmente los Principios I (Monolito por diseño) y II (Separación de responsabilidades dentro del monolito).
- Garantiza que ninguna ruta HTTP acceda a los modelos saltándose la capa de servicios.
- Permite que toda la lógica de dominio se ejecute y pruebe sin levantar un servidor web ni simular clientes HTTP.

### Alternativas Evaluadas y Rechazadas
- **Arquitectura de microservicios**: Rechazada taxativamente por el Principio I de la constitución.
- **Rutas con lógica de base de datos directa (ActiveRecord / fat controllers)**: Rechazada porque acopla el protocolo HTTP con las transacciones de base de datos, violando el Principio II.

---

## 2. Estrategia de Autenticación y Manejo de Sesión (Principio VII)

### Decisión
- **Almacenamiento de contraseñas**: Se utilizará `werkzeug.security.generate_password_hash` y `werkzeug.security.check_password_hash` con método `scrypt` o `pbkdf2:sha256` (incorporado nativamente en Werkzeug/Python sin dependencias C externas complejas) para garantizar que ninguna contraseña toque la base de datos en texto plano.
- **Sesión de usuario**: Se empleará la sesión nativa de Flask (`flask.session`) respaldada por cookies criptográficamente firmadas con `SECRET_KEY` provista por variable de entorno (`.env`).
- **Verificación en Backend**: Se implementará un decorador `@login_required` o middleware a nivel de servicio/ruta que inspeccione `session.get('user_id')`. Si no existe sesión válida o el usuario no existe en la base de datos, se interrumpe la ejecución devolviendo HTTP 401 (o redirección a `/auth/login` para vistas HTML), impidiendo cualquier mutación de datos.

### Razón de ser
- Cumple con el Principio VII (Seguridad por defecto) asegurando verificación obligatoria en el backend.
- Evita introducir dependencias excesivas o pesadas (como OAuth o JWT complejos para un monolito Jinja2), siguiendo el Principio V (YAGNI).

---

## 3. Modelado de Datos y Relaciones con SQLAlchemy (Principio II y VI)

### Decisión
- Modelos centrales:
  - `User`: `id` (PK, Integer), `email` (String(255), unique=True, nullable=False, indexed=True), `password_hash` (String(255), nullable=False), `created_at` (DateTime UTC).
  - `Task`: `id` (PK, Integer), `user_id` (FK a users.id, nullable=False, indexed=True), `title` (String(150), nullable=False), `description` (Text, nullable=True), `due_date` (Date/DateTime, nullable=True), `status` (Enum: `'pending'`, `'in_progress'`, `'completed'`, default='pending'), `created_at`, `updated_at`.
  - `AuditLog`: `id` (PK, Integer), `actor_id` (Integer, nullable=False, indexed=True), `action` (String(50), nullable=False), `entity_id` (Integer, nullable=False, indexed=True), `timestamp` (DateTime UTC, nullable=False), `details` (JSON / Text, nullable=True).
- Relación: `User` tiene relación `1 a N` con `Task`. Toda consulta de tareas filtra estrictamente por `user_id = current_user.id`.

### Razón de ser
- Proporciona aislamiento estricto de tareas por usuario (previene vulnerabilidades IDOR).
- El modelo `AuditLog` desacoplado garantiza persistencia inmutable para observabilidad.

---

## 4. Estrategia de Migraciones de Base de Datos (Principio VI)

### Decisión
- Utilizar `Flask-Migrate` (wrapper oficial de Alembic para Flask).
- Inicialización en desarrollo: `flask db init`.
- Generación de migración inicial: `flask db migrate -m "init_users_tasks_audit"`.
- Aplicación de esquema: `flask db upgrade`.
- Se prohíbe el uso de `db.create_all()` en flujos de producción o migraciones reales.

### Razón de ser
- Cumple el Principio VI (Integridad de datos y migraciones): todo cambio de esquema es versionado, auditable y reproducible mediante código en `migrations/versions/`.

---

## 5. Estrategia de Logging Estructurado y Auditoría (Principio VIII)

### Decisión
- Centralizar la generación de eventos de auditoría en la capa de servicios (`src/taskcontrol/services/audit_service.py`), invocado directamente por `task_service.py` en cada operación de creación o mutación de estado.
- Salida doble:
  1. **Persistencia relacional**: Registro en la tabla `AuditLog` para consultas históricas y trazabilidad.
  2. **Log estructurado de aplicación**: Emisión con el módulo `logging` de Python en formato JSON estandarizado hacia `stdout`/archivo de log:
     ```json
     {"timestamp": "2026-09-29T15:30:00Z", "actor_id": 1, "action": "STATUS_CHANGED", "entity_id": 42, "details": {"old_status": "pending", "new_status": "in_progress"}}
     ```

### Razón de ser
- Cumple con el Principio VIII (Observabilidad mínima viable). Centralizarlo en la capa de servicio evita la duplicación de código en los blueprints HTTP y garantiza que ninguna mutación de tarea se ejecute sin auditoría.

---

## 6. Estrategia de Pruebas Test-First (Principio IV)

### Decisión
- **Herramienta**: `pytest` como runner de pruebas.
- **Estructura de pruebas**:
  - `tests/unit/`: Pruebas de modelos y utilidades de validación.
  - `tests/services/`: **Bloqueante** según Principio IV. Pruebas que validan:
    - Reglas de negocio de `UserService` (registro con email duplicado, hash de contraseña, verificación).
    - Reglas de negocio de `TaskService` (creación con título vacío, transiciones de estado válidas `pending` → `in_progress` → `completed`, rechazo de reapertura `completed` → `pending`, asignación de propietario, aislamiento entre usuarios).
  - `tests/functional/`: Pruebas de integración de rutas HTTP (status codes 200, 201, 302, 400, 401, 403, 404, cookies de sesión).

### Razón de ser
- Asegura que el ciclo *Red-Green-Refactor* del Principio IV se aplique rigurosamente antes de construir las vistas y rutas.
