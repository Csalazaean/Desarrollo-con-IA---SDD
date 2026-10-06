# Quickstart & Verification Guide: 002-task-closure-recovery

**Feature**: `002-task-closure-recovery`  
**Date**: 2026-10-01  

---

## 1. Prerrequisitos y Configuración de Entorno

Asegúrate de estar en el directorio raíz del proyecto con el entorno virtual activo:

```powershell
# En Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Instalar o actualizar dependencias si fuese necesario
pip install -r requirements.txt
```

---

## 2. Ejecución de Migraciones de Base de Datos (Principio VI)

Aplica las migraciones para incorporar las columnas de eliminación lógica a `tasks` y la tabla `password_reset_tokens`:

```powershell
flask db upgrade
```

---

## 3. Ejecución de la Suite de Pruebas Automatizadas (Principio IV)

Ejecuta las pruebas en orden de criticidad arquitectónica:

```powershell
# 1. Pruebas bloqueantes de dominio y servicios (Test-First)
pytest tests/services/test_task_service.py tests/services/test_user_service.py -v

# 2. Pruebas de integración HTTP y rutas
pytest tests/functional/ -v

# 3. Cobertura completa del proyecto
pytest -v
```

---

## 4. Verificación de Escenarios de Negocio End-to-End

Inicia la aplicación:
```powershell
flask run
```

### Escenario A: Eliminación Lógica de Tareas (HU-05)
1. Inicia sesión con un usuario existente y crea una tarea "Tarea de Prueba para Eliminación".
2. En el listado de tareas, presiona el botón **Eliminar**.
3. **Verificación visual**: La tarea desaparece inmediatamente del listado principal.
4. **Verificación en BD**: Al consultar la base de datos con SQLite (`sqlite3 instance/taskcontrol.db "SELECT id, title, is_deleted, deleted_at FROM tasks WHERE id = <ID>;"`), el registro sigue existiendo con `is_deleted = 1` y una marca de tiempo en `deleted_at`.
5. **Verificación de auditoría**: Consulta la tabla `audit_logs`: debe existir un registro con `action = 'TASK_DELETED'`.
6. **Verificación de no re-eliminación**: Intentar enviar un POST manual a `/tasks/<ID>/delete` debe retornar error indicando que la tarea ya fue eliminada.

### Escenario B: Reapertura de Tareas Completadas (HU-06)
1. Marca una tarea activa como "completada".
2. En la sección de completadas, pulsa la acción explícita **Reabrir**.
3. **Verificación visual**: La tarea retorna a estado "pendiente" en la vista principal.
4. **Verificación de auditoría**: En `audit_logs` figura un evento con `action = 'TASK_REOPENED'` con detalle `{ "previous_status": "completed", "new_status": "pending" }`.

### Escenario C: Recuperación de Acceso y Uso Único de Token (HU-14)
1. Cierra sesión y dirígete a `/auth/forgot-password`.
2. Ingresa un correo NO registrado: observa que la pantalla devuelve el mensaje neutro de confirmación sin filtrar error.
3. Ingresa tu correo registrado: observa el mismo mensaje neutro de confirmación.
4. En la consola/terminal del servidor donde corre Flask, visualiza la línea generada por el logger:
   `[PASSWORD RESET SIMULATION] Enlace de restablecimiento generado: http://127.0.0.1:5000/auth/reset-password/<TOKEN>`
5. Abre el enlace en el navegador, ingresa una nueva contraseña y confirma.
6. Inicia sesión con la nueva contraseña: el acceso debe ser exitoso.
7. Vuelve a abrir el mismo enlace o recarga la página: el sistema debe rechazarlo indicando que el enlace es inválido o ya ha sido utilizado.
