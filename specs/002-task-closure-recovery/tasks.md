# Tasks: 002-task-closure-recovery

**Feature**: 002-task-closure-recovery (Cierre de gestión básica de tareas y recuperación de acceso)  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Date**: 2026-10-05  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparación de configuraciones compartidas y constantes del segundo incremento.

- [ ] T001 [P] Configure password reset token expiration setting `PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES = 30` in `src/taskcontrol/config.py`
- [ ] T002 [P] Update audit log action definitions and documentation in `src/taskcontrol/models/audit.py` to support `TASK_DELETED`, `TASK_REOPENED`, `PASSWORD_RESET_REQUESTED`, and `PASSWORD_RESET_COMPLETED` per Principle VIII

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura bloqueante del modelo relacional y migraciones de esquema requeridas por todas las historias de usuario.

**CRITICAL**: Ninguna historia de usuario puede implementarse hasta que los modelos y migraciones de esta fase estén listos y verificados.

- [ ] T003 Extend `Task` model in `src/taskcontrol/models/task.py` with constraints `is_deleted (Boolean, default False, Not Null, Index)` and `deleted_at (DateTime UTC, Nullable)` per `data-model.md`
- [ ] T004 [P] Create `PasswordResetToken` model in `src/taskcontrol/models/password_reset.py` with constraints `id (PK, Integer, autoincrement)`, `user_id (Integer, FK users.id, Not Null, Index)`, `token_hash (String(64), Not Null, Index)`, `expires_at (DateTime UTC, Not Null)`, `used_at (DateTime UTC, Nullable)` and `created_at (DateTime UTC, Not Null, default UTC)` per `data-model.md`
- [ ] T005 [P] Register and export `PasswordResetToken` in `src/taskcontrol/models/__init__.py`
- [ ] T006 Create Alembic migration script in `migrations/versions/` adding `is_deleted` (with `server_default='0'`), `deleted_at`, index `ix_tasks_is_deleted` to table `tasks`, and creating table `password_reset_tokens` per Principle VI

**Checkpoint**: Esquema y modelos relacionales listos. La implementación de historias de usuario puede comenzar.

---

## Phase 3: User Story 1 - Eliminación Lógica de Tareas (HU-05) (Priority: P1) 🎯 MVP Core

**Goal**: Permitir al usuario autenticado eliminar lógicamente tareas propias (soft delete) garantizando que no se borren físicamente, se excluyan del listado principal y registren auditoría `TASK_DELETED`.

**Independent Test**: Crear una tarea como usuario autenticado, solicitar su eliminación y verificar que:
1. Desaparece del listado por defecto (`get_user_tasks` y `/tasks`).
2. El registro en la tabla `tasks` permanece intacto con `is_deleted = True` y `deleted_at` fijado.
3. Se genera un registro inmutable en `AuditLog` con acción `TASK_DELETED`.
4. Intentar eliminarla nuevamente arroja error `TaskAlreadyDeletedError` (código HTTP 400 o 409).
5. Intentar eliminarla con otro usuario arroja `TaskNotFoundError` (404 Not Found).

### Tests for User Story 1 (Test-First bloqueante - Principio IV) ⚠️
> **NOTA: Escribir estas pruebas primero y verificar que FALLAN antes de implementar el código de producción**

- [ ] T007 [P] [US1] Write failing service tests for soft delete in `tests/services/test_task_service.py` (`test_soft_delete_task_marks_deleted_and_sets_timestamp`, `test_soft_delete_preserves_task_in_database_and_audit_history`, `test_deleted_task_excluded_from_default_listing`, `test_cannot_delete_already_deleted_task`, `test_cannot_edit_deleted_task`, `test_delete_task_unauthorized_or_not_found`)
- [ ] T008 [P] [US1] Write failing functional tests for delete endpoint in `tests/functional/test_task_routes.py` (`test_delete_task_endpoint_success_json_and_html`, `test_delete_task_endpoint_unauthorized`, `test_delete_task_endpoint_not_found_for_other_user`, `test_delete_task_endpoint_already_deleted_returns_error`)

### Implementation for User Story 1
- [ ] T009 [US1] Define `TaskAlreadyDeletedError` exception in `src/taskcontrol/services/task_service.py`
- [ ] T010 [US1] Update `get_user_tasks` and `get_task_by_id` in `src/taskcontrol/services/task_service.py` to filter `is_deleted == False` by default and raise `TaskNotFoundError` if accessing a deleted task
- [ ] T011 [US1] Implement `delete_task(task_id, user_id)` in `src/taskcontrol/services/task_service.py` setting `is_deleted = True`, `deleted_at = now_utc`, persisting changes, preventing double deletion via `TaskAlreadyDeletedError`, and logging audit action `TASK_DELETED` per Principle VIII
- [ ] T012 [US1] Guard `update_task_details` and `update_task_status` in `src/taskcontrol/services/task_service.py` to prevent modifying deleted tasks
- [ ] T013 [US1] Implement route handler `POST /tasks/<int:task_id>/delete` (and support `DELETE /tasks/<int:task_id>`) in `src/taskcontrol/routes/tasks.py` supporting JSON and HTML flash redirection per `specs/002-task-closure-recovery/contracts/task-contracts.md`
- [ ] T014 [US1] Add delete action button and modal/confirmation form in `src/taskcontrol/templates/tasks/index.html`

**Checkpoint**: User Story 1 completa y verificada con pruebas automatizadas en verde.

---

## Phase 4: User Story 2 - Reapertura de Tareas Completadas (HU-06) (Priority: P1)

**Goal**: Permitir al usuario autenticado reabrir una tarea en estado `completed` regresándola a estado activo `pending` y auditando el evento específico `TASK_REOPENED`.

**Independent Test**: Marcar una tarea como completada, ejecutar la reapertura y verificar que:
1. Su estado cambia a `pending`.
2. En `AuditLog` se registra un evento con acción `TASK_REOPENED` con detalles estructurados `{"previous_status": "completed", "new_status": "pending", "trigger": "user_reopen"}`.
3. Si la tarea está en estado `pending` o `in_progress`, o si está eliminada lógicamente, la reapertura es rechazada con código de error.

### Tests for User Story 2 (Test-First bloqueante - Principio IV) ⚠️
> **NOTA: Escribir estas pruebas primero y verificar que FALLAN antes de implementar el código de producción**

- [ ] T015 [P] [US2] Write failing service tests for task reopening in `tests/services/test_task_service.py` (`test_reopen_completed_task_success`, `test_reopen_task_generates_specific_task_reopened_audit_log`, `test_cannot_reopen_non_completed_task`, `test_cannot_reopen_deleted_task`)
- [ ] T016 [P] [US2] Write failing functional tests for reopen endpoint in `tests/functional/test_task_routes.py` (`test_reopen_task_endpoint_success`, `test_reopen_task_endpoint_invalid_state`, `test_reopen_task_endpoint_unauthorized`, `test_reopen_task_endpoint_not_found`)

### Implementation for User Story 2
- [ ] T017 [US2] Implement `reopen_task(task_id, user_id)` in `src/taskcontrol/services/task_service.py` validating that `task.status == 'completed'` and `task.is_deleted is False`, updating status to `'pending'`, and recording audit event `TASK_REOPENED` per Principle VIII
- [ ] T018 [US2] Implement route handler `POST /tasks/<int:task_id>/reopen` in `src/taskcontrol/routes/tasks.py` returning JSON or redirecting to `/tasks` per `specs/002-task-closure-recovery/contracts/task-contracts.md`
- [ ] T019 [US2] Add reopen button and action triggers for completed tasks in `src/taskcontrol/templates/tasks/index.html`

**Checkpoint**: User Stories 1 y 2 completamente funcionales y auditadas.

---

## Phase 5: User Story 3 - Recuperación Segura de Contraseña (HU-14) (Priority: P2)

**Goal**: Permitir la recuperación de contraseñas mediante solicitud neutra por correo electrónico, tokens temporales criptográficos de 30 minutos almacenados exclusivamente como hash SHA-256 e invalidación atómica tras su uso.

**Independent Test**:
1. Solicitar recuperación con un correo existente y con uno inexistente: ambas respuestas deben ser idénticas y neutras (código 200 OK con mensaje neutro, 0% de fuga de información).
2. Verificar que en la base de datos se almacena únicamente el hash SHA-256 (64 caracteres hexadecimales) y no el token en texto plano.
3. Usar el token válido para cambiar la contraseña: la nueva contraseña debe permitir login y el token debe quedar invalidado (`used_at` registrado).
4. Reintentar usar el mismo token o uno expirado: la solicitud debe ser rechazada.

### Tests for User Story 3 (Test-First bloqueante - Principio IV) ⚠️
> **NOTA: Escribir estas pruebas primero y verificar que FALLAN antes de implementar el código de producción**

- [ ] T020 [P] [US3] Write failing service tests for password reset in `tests/services/test_user_service.py` (`test_password_reset_request_neutral_response_existing_and_non_existing_email`, `test_password_reset_token_hashed_in_database`, `test_password_reset_token_expiration`, `test_password_reset_success_updates_password_and_invalidates_token`, `test_cannot_reuse_already_used_reset_token`, `test_multiple_reset_requests_invalidates_previous_pending_tokens`, `test_audit_logs_for_password_reset_requested_and_completed`)
- [ ] T021 [P] [US3] Write failing functional tests for auth recovery endpoints in `tests/functional/test_auth_routes.py` (`test_forgot_password_endpoint_neutral_response`, `test_forgot_password_invalid_email_format`, `test_reset_password_get_endpoint_valid_and_invalid_token`, `test_reset_password_post_endpoint_success`, `test_reset_password_post_password_mismatch_or_short`, `test_reset_password_post_used_or_expired_token`)

### Implementation for User Story 3
- [ ] T022 [US3] Implement `request_password_reset(email)` in `src/taskcontrol/services/user_service.py` with email normalization, neutral return, token generation via `secrets.token_urlsafe(32)`, SHA-256 hashing, 30-minute expiration, invalidation of prior pending tokens, console link log simulation via `app.logger.info`, and audit logging `PASSWORD_RESET_REQUESTED`
- [ ] T023 [US3] Implement `verify_reset_token(raw_token)` and `reset_password(raw_token, new_password)` in `src/taskcontrol/services/user_service.py` with password length validation (min 8 chars), atomic update of `user.password_hash` and `token.used_at`, and audit logging `PASSWORD_RESET_COMPLETED` per Principle VII and VIII
- [ ] T024 [P] [US3] Create password recovery request template in `src/taskcontrol/templates/auth/forgot_password.html` with email form and neutral message display
- [ ] T025 [P] [US3] Create password reset confirmation template in `src/taskcontrol/templates/auth/reset_password.html` with new password and confirmation password fields
- [ ] T026 [US3] Implement route handlers `GET` and `POST /auth/forgot-password` in `src/taskcontrol/routes/auth.py` per `specs/002-task-closure-recovery/contracts/auth-contracts.md`
- [ ] T027 [US3] Implement route handlers `GET` and `POST /auth/reset-password/<string:token>` in `src/taskcontrol/routes/auth.py` per `specs/002-task-closure-recovery/contracts/auth-contracts.md`
- [ ] T028 [US3] Add link to "Olvidé mi contraseña" in login template `src/taskcontrol/templates/auth/login.html`

**Checkpoint**: Flujo de recuperación de contraseñas completamente implementado, seguro y probado.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación global, integración cliente y aseguramiento de calidad del incremento.

- [ ] T029 [P] Update client-side JavaScript handlers in `src/taskcontrol/static/js/main.js` to support interactive deletion and reopening confirmations
- [ ] T030 Run full automated test suite with `pytest` ensuring 100% passing tests and zero regressions across all increments
- [ ] T031 Validate integration scenarios and manual curl/browser workflows per `specs/002-task-closure-recovery/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion.
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) completion. Integrates with task model and service, can proceed alongside or after US1.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) completion. Focuses on authentication domain and is completely decoupled from US1/US2.
- **Polish (Phase 6)**: Depends on all user stories (US1, US2, US3) being completed.

### User Story Dependencies

- **User Story 1 (P1 - HU-05 Soft Delete)**: Operates on `Task` and `TaskService`. Independent of US2 and US3.
- **User Story 2 (P1 - HU-06 Reopen Task)**: Extends `TaskService` state machine (`completed` → `pending`). Reuses soft delete guard from US1 to ensure deleted tasks cannot be reopened.
- **User Story 3 (P2 - HU-14 Password Recovery)**: Operates on `User`, `PasswordResetToken` and `UserService`. No runtime dependencies on `Task`.

### Within Each User Story

- Test-first tests MUST be written and verified FAILING before implementing production logic (Principio IV).
- Models and exceptions before services.
- Services before HTTP routes/controllers.
- Route controllers before templates and client UI.
- Story complete and verified before declaring checkpoint passed.

### Parallel Opportunities

- **Phase 1**: T001 and T002 can execute in parallel.
- **Phase 2**: T004 and T005 can execute in parallel while T003 is prepared.
- **Phase 3**: T007 (service tests) and T008 (route tests) can be written in parallel.
- **Phase 4**: T015 (service tests) and T016 (route tests) can be written in parallel.
- **Phase 5**: T020 (service tests) and T021 (route tests) can be written in parallel; templates T024 and T025 can be authored in parallel.
- **Across Stories**: Once Phase 2 is complete, US1/US2 (Task domain) and US3 (Auth domain) can be developed independently.

---

## Parallel Example: User Story 1

```bash
# Launch test creation tasks together (Test-First):
Task: "T007 [P] [US1] Write failing service tests for soft delete in tests/services/test_task_service.py"
Task: "T008 [P] [US1] Write failing functional tests for delete endpoint in tests/functional/test_task_routes.py"
```

## Parallel Example: User Story 3

```bash
# Launch test creation tasks together:
Task: "T020 [P] [US3] Write failing service tests for password reset in tests/services/test_user_service.py"
Task: "T021 [P] [US3] Write failing functional tests for auth recovery endpoints in tests/functional/test_auth_routes.py"

# Launch templates creation together:
Task: "T024 [P] [US3] Create password recovery request template in src/taskcontrol/templates/auth/forgot_password.html"
Task: "T025 [P] [US3] Create password reset confirmation template in src/taskcontrol/templates/auth/reset_password.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (`config.py`, audit actions).
2. Complete Phase 2: Foundational (Task schema extension, `PasswordResetToken`, Alembic migration).
3. Complete Phase 3: User Story 1 (Soft delete).
4. **STOP and VALIDATE**: Run `pytest tests/services/test_task_service.py` and `pytest tests/functional/test_task_routes.py`.
5. Verify soft delete behaves with zero physical deletions and complete audit logging.

### Incremental Delivery
1. Foundation complete → Base ready.
2. Deliver US1 (Soft Delete) → Test independently.
3. Deliver US2 (Reopen Task) → Test independently (validates state transition `completed` → `pending` and `TASK_REOPENED` log).
4. Deliver US3 (Password Recovery) → Test independently (validates neutral response, SHA-256 tokens, 30-min expiration, single-use invalidation).
5. Complete Phase 6: Polish & Cross-Cutting Concerns → Run full test suite.
