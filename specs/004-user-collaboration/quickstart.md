# Quickstart & Verification Guide: 004-user-collaboration

**Feature**: `004-user-collaboration`
**Date**: 2026-10-06

---

## 1. Prerrequisitos y Configuración de Entorno

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Aplicación de Migraciones de Base de Datos (Principio VI)

Aplica la migración que agrega `assigned_to_id` a `tasks` y crea la tabla `notifications`:

```powershell
flask db upgrade
```

---

## 3. Ejecución de Pruebas Automatizadas (Principio IV)

```powershell
# 1. Pruebas de dominio y servicios (Test-First)
pytest tests/services/test_task_service.py tests/services/test_notification_service.py -v

# 2. Pruebas de integración HTTP
pytest tests/functional/ -v

# 3. Suite completa
pytest -v
```

---

## 4. Verificación de Escenarios E2E

Inicia la aplicación con dos usuarios registrados (Usuario A y Usuario B):
```powershell
flask run
```

### Escenario A: Asignación de Tareas (HU-10)
1. Inicia sesión como Usuario A y crea una tarea "Preparar informe".
2. Asigna la tarea al correo del Usuario B.
3. **Verificación**: en `AuditLog` aparece un evento `TASK_ASSIGNED` con el detalle del correo asignado.
4. Cierra sesión e inicia sesión como Usuario B: la tarea aparece en su listado, pestaña "Asignadas a mí", con la etiqueta "Asignada por [correo de A]".
5. Como Usuario A, retira la asignación: la tarea desaparece del listado de B y vuelve a "Sin asignar" para A — verifica que **no** se generó notificación para B por este retiro.
6. Intenta asignar la tarea a un correo no registrado: debe rechazarse con error claro, sin modificar la tarea.

### Escenario B: Notificaciones Internas (HU-11)
1. Como Usuario A, asigna una tarea nueva al Usuario B.
2. Inicia sesión como Usuario B: el contador de notificaciones no leídas en la barra de navegación muestra al menos 1.
3. Entra a `/notifications`: la notificación aparece con el título de la tarea y el correo de A.
4. Márcala como leída: el contador decrementa, y la notificación **permanece visible** en el historial.
5. Repite el marcado de lectura sobre la misma notificación: no debe producir error (idempotencia).
6. Como Usuario A, autoasígnate una tarea propia: verifica que **no** se generó ninguna notificación para ti mismo.

### Escenario C: Aislamiento y Autorización
1. Como Usuario B (no creador), intenta reasignar la tarea que A le asignó a un tercero: debe rechazarse (403/404).
2. Como Usuario B, intenta acceder vía API a una notificación perteneciente a otro usuario: debe responder 404, nunca revelar su existencia.
