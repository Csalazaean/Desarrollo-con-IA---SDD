# Quickstart & Guía de Validación: 001-basic-tasks-auth

**Feature**: 001-basic-tasks-auth  
**Date**: 2026-09-29  

Esta guía define los pasos de configuración, ejecución con un solo comando y validación integral de extremo a extremo para el primer incremento funcional de **TaskControl**.

---

## 1. Prerrequisitos y Configuración Inicial

- **Python**: 3.11 o superior.
- **Gestor de entorno virtual**: `venv` de Python.

### Preparación del entorno local
```powershell
# Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### Variables de entorno (`.env`)
Crear un archivo `.env` en la raíz del proyecto (nunca versionado):
```env
FLASK_APP=src/taskcontrol
FLASK_ENV=development
SECRET_KEY=clave_secreta_para_desarrollo_local_taskcontrol_2026
DATABASE_URL=sqlite:///taskcontrol_dev.db
```

---

## 2. Inicialización de Base de Datos y Migraciones (Principio VI)

```powershell
# Inicializar repositorio de migraciones (solo la primera vez)
flask db init

# Generar la migración inicial para User, Task y AuditLog
flask db migrate -m "init_users_tasks_audit"

# Aplicar las migraciones al esquema de SQLite
flask db upgrade
```

---

## 3. Ejecución con un Solo Comando

Tal como exige la sección de restricciones técnicas de la constitución, el servidor se levanta con un único comando:

```powershell
flask run --port 5000
```
O mediante el script de inicio unificado:
```powershell
.\run.ps1
```
La aplicación estará disponible en `http://127.0.0.1:5000`.

---

## 4. Ejecución de la Suite de Pruebas Automatizadas (Principio IV)

Para verificar el cumplimiento del enfoque *test-first* y la cobertura del dominio antes de la entrega:

```powershell
# Ejecutar todas las pruebas con pytest
pytest -v

# Ejecutar únicamente las pruebas bloqueantes de la capa de servicios
pytest tests/services/ -v

# Ejecutar pruebas de contratos y rutas HTTP
pytest tests/functional/ -v
```

---

## 5. Escenarios de Validación Manual de Extremo a Extremo

### Escenario 1: Registro e Inicio de Sesión (`HU-12`, `HU-13`)
1. Navegar a `http://127.0.0.1:5000/auth/register`.
2. Registrar un nuevo usuario con correo `test@taskcontrol.dev` y contraseña `TestPassword2026!`.
3. Validar que la cuenta se cree y redirija al login.
4. Iniciar sesión con las credenciales registradas.
5. Comprobar que se establece la cookie de sesión y se redirige a `/tasks`.

### Escenario 2: Creación y Listado de Tareas (`HU-01`, `HU-02`)
1. Estando autenticado, en la página `/tasks`, ingresar un título (ej: `"Mi primera tarea"`) y fecha límite.
2. Hacer clic en "Crear Tarea".
3. Verificar que la tarea aparezca en el listado con estado `pending`.
4. Verificar en consola o log estructurado que se emitió el evento de auditoría `TASK_CREATED`.

### Escenario 3: Cambio de Estado y Filtrado (`HU-03`, `HU-02`)
1. En la tarea creada, cambiar el estado a `in_progress`.
2. Verificar que el badge de estado se actualice y que se registre `STATUS_CHANGED`.
3. Cambiar de nuevo el estado a `completed`.
4. Probar los filtros por estado (`Todos`, `Pendientes`, `En Progreso`, `Completadas`) y verificar que se filtre correctamente.
5. Intentar cambiar la tarea de `completed` a `pending` y comprobar que la interfaz y el backend lo rechazan (reapertura bloqueada).

### Escenario 4: Edición de Tareas (`HU-04`)
1. Abrir la tarea y modificar el título a `"Mi primera tarea (Actualizada)"`.
2. Guardar y verificar que el cambio persista y se emita el log `TASK_UPDATED`.
3. Intentar guardar un título vacío y comprobar que el backend rechaza la edición mostrando un error de validación.

### Escenario 5: Cierre de Sesión y Protección de Rutas (`HU-13`, Principio VII)
1. Hacer clic en "Cerrar Sesión".
2. Intentar acceder directamente a `http://127.0.0.1:5000/tasks` o enviar un `POST /tasks`.
3. Comprobar que el backend bloquea la petición redirigiendo a login o respondiendo con código 401.
