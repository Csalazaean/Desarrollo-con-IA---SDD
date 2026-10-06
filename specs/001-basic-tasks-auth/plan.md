# Implementation Plan: 001-basic-tasks-auth

**Branch**: `001-basic-tasks-auth` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-basic-tasks-auth/spec.md`

---

## Summary

Implementar el primer incremento funcional del monolito **TaskControl**: sistema de registro e inicio/cierre de sesión seguro con hash de contraseñas (`HU-12`, `HU-13`), junto con la gestión esencial de tareas (`HU-01` a `HU-04`: creación con estado inicial "pendiente", listado filtrado por estado exclusivo del usuario autenticado, transiciones de estado válidas y edición de datos).

El desarrollo sigue una arquitectura monolítica estricta en 4 capas desacopladas (Presentación Jinja2/JS → Blueprints Flask → Servicios de dominio → Modelos SQLAlchemy), con validación obligatoria en backend, auditoría estructurada inmutable de cada mutación y enfoque *test-first* bloqueante en la capa de servicios.

---

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.x, SQLAlchemy (Flask-SQLAlchemy), Flask-Migrate (Alembic), Werkzeug (security / password hashing)  
**Storage**: Base de datos relacional SQLite (desarrollo/pruebas locales) / PostgreSQL-compatible  
**Testing**: pytest (pytest-flask)  
**Target Platform**: Linux / Windows / macOS server (proceso monolítico único)  
**Project Type**: Monolito web (Jinja2 renderizado en servidor + JavaScript vanilla para interactividad ligera)  
**Performance Goals**: Tiempo de respuesta < 100ms para consultas de listado local; < 150ms para operaciones con hash de contraseña  
**Constraints**: 
- Cero microservicios y cero colas de mensajes externas (Principio I).
- Estricta separación en 4 capas sin saltos entre niveles (Principio II).
- Contratos HTTP explícitos documentados previamente (Principio III).
- TDD obligatorio y bloqueante en la capa de servicios (Principio IV).
- Migraciones reproducibles con Flask-Migrate (Principio VI).
- Verificación de sesión en backend en cada endpoint mutador (Principio VII).
- Log estructurado en cada mutación de tarea (Principio VIII).  
**Scale/Scope**: Incremento inicial MVP (6 Historias de Usuario: HU-01..HU-04, HU-12..HU-13)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio Constitucional | Estado | Justificación / Mecanismo de Cumplimiento |
|---|---|---|
| **I. Monolito por diseño** | **PASS** | Un único repositorio, un único proceso web desplegable en Flask, una única base de datos relacional. Sin microservicios ni colas asíncronas externas. |
| **II. Separación de responsabilidades** | **PASS** | Estructura en 4 capas estrictas (`models/` → `services/` → `routes/` → `templates/`). Las rutas solo procesan HTTP y delegan a servicios; nunca consultan modelos directamente. |
| **III. Contrato explícito** | **PASS** | Todos los endpoints de autenticación y tareas cuentan con contratos HTTP formalizados en `specs/001-basic-tasks-auth/contracts/` previo a la codificación. |
| **IV. Test-first en lógica de negocio** | **PASS** | La suite `tests/services/` valida reglas de transición, validaciones de título y unicidad de correo en ciclo *Red-Green-Refactor* antes de implementar código funcional. |
| **V. Simplicidad (YAGNI)** | **PASS** | Sin frameworks SPA pesados, sin abstracciones innecesarias; sesiones nativas de Flask y hash seguro con Werkzeug. |
| **VI. Integridad de datos y migraciones** | **PASS** | Control estricto de esquema relacional mediante `Flask-Migrate` (`flask db init / migrate / upgrade`). Prohibido alterar el esquema manualmente. |
| **VII. Seguridad por defecto** | **PASS** | Hash seguro de contraseñas, validación en backend independiente de la interfaz, decorador `@login_required` para verificación de sesión en backend, secretos en `.env`. |
| **VIII. Observabilidad mínima viable** | **PASS** | Modelo `AuditLog` y logger estructurado JSON centralizados en `audit_service.py` registrando `actor_id`, `action`, `entity_id` y `timestamp` en cada mutación. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-basic-tasks-auth/
├── spec.md              # Especificación funcional validada
├── plan.md              # Este plan de implementación técnica
├── research.md          # Investigación y decisiones arquitectónicas (Fase 0)
├── data-model.md        # Esquema de datos, ERD y máquina de estados (Fase 1)
├── quickstart.md        # Guía de inicialización y verificación E2E (Fase 1)
├── contracts/           # Contratos explícitos de endpoints HTTP (Fase 1)
│   ├── auth-contracts.md
│   └── task-contracts.md
└── checklists/
    └── requirements.md  # Checklist de calidad de requisitos
```

### Source Code (repository root)

```text
src/
└── taskcontrol/
    ├── __init__.py           # Application Factory: create_app()
    ├── config.py             # Configuración cargada desde variables de entorno (.env)
    ├── extensions.py         # Instancias centralizadas: db (SQLAlchemy), migrate (Flask-Migrate)
    │
    ├── models/               # Capa 4: Persistencia y datos
    │   ├── __init__.py
    │   ├── user.py           # Modelo User (id, email, password_hash, created_at)
    │   ├── task.py           # Modelo Task (id, user_id, title, description, due_date, status, timestamps)
    │   └── audit.py          # Modelo AuditLog (id, actor_id, action, entity_id, timestamp, details)
    │
    ├── services/             # Capa 3: Lógica de negocio de dominio (Test-first bloqueante)
    │   ├── __init__.py
    │   ├── user_service.py   # Registro, verificación de contraseñas, validación de email
    │   ├── task_service.py   # Creación, filtrado por usuario, máquina de estados, validaciones
    │   └── audit_service.py  # Centralización de auditoría estructurada y logging JSON
    │
    ├── routes/               # Capa 2: Blueprints HTTP (Transporte, deserialización y sesión)
    │   ├── __init__.py
    │   ├── auth.py           # Blueprint /auth (register, login, logout)
    │   ├── tasks.py          # Blueprint /tasks (list, create, edit, status)
    │   └── main.py           # Blueprint raíz (redirección a /tasks o /auth/login)
    │
    ├── templates/            # Capa 1: Presentación Jinja2
    │   ├── base.html         # Plantilla maestra con navbar y mensajes flash
    │   ├── auth/
    │   │   ├── login.html    # Formulario de inicio de sesión
    │   │   └── register.html # Formulario de registro de usuario
    │   └── tasks/
    │       ├── index.html    # Listado de tareas con filtros de estado y modal/form de creación
    │       └── edit.html     # Formulario de edición de tarea
    │
    └── static/               # Capa 1: Activos estáticos cliente
        ├── css/
        │   └── styles.css    # Estilos limpios y accesibles
        └── js/
            └── main.js       # JavaScript vanilla ligero para interactividad básica

tests/
├── __init__.py
├── conftest.py               # Fixtures: app de prueba, base de datos en memoria, cliente HTTP
├── services/                 # Pruebas de dominio (BLOQUEANTE según Principio IV)
│   ├── test_user_service.py  # Unicidad de correo, hashing, validaciones
│   └── test_task_service.py  # Máquina de estados, aislamiento de usuario, auditoría
└── functional/               # Pruebas de integración HTTP
    ├── test_auth_routes.py   # Registro, login, logout, cookies de sesión
    └── test_task_routes.py   # CRUD de tareas, 401 sin sesión, 403 entre usuarios

migrations/                   # Scripts versionados de Alembic / Flask-Migrate
requirements.txt              # Dependencias fijadas del proyecto
run.ps1                       # Script de ejecución con un solo comando
```

**Structure Decision**: Monolito único empaquetado en Python con separación física y lógica en 4 directorios claros (`models/`, `services/`, `routes/`, `templates/` + `static/`), permitiendo pruebas totalmente aisladas de la lógica de negocio y control estricto del flujo de dependencias entre capas.

---

## Complexity Tracking

> **Estado**: Sin violaciones constitucionales. Todas las decisiones arquitectónicas respetan los límites de simplicidad (YAGNI), monolito y observabilidad sin requerir justificaciones de complejidad extra.

| Elemento | Justificación | Alternativa Más Simple Rechazada |
|---|---|---|
| Modelo `AuditLog` dedicado | Requerido explícitamente por el Principio VIII de la constitución para observabilidad estructurada. | Logs exclusivos a texto plano rechazados porque no permiten trazabilidad transaccional integrada con la base de datos relacional. |
| Capa de Servicios (`services/`) | Requerida explícitamente por el Principio II para evitar lógica de negocio en rutas o en modelos. | Poner lógica en rutas rechazada taxativamente por violar el desacoplamiento y el Principio IV (test-first en dominio). |
