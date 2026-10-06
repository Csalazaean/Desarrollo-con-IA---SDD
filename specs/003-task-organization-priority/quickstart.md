# Quickstart & Verification Guide: 003-task-organization-priority

**Feature**: `003-task-organization-priority`  
**Date**: 2026-10-01  

---

## 1. Prerrequisitos y Configuración de Entorno

```powershell
# En Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Asegurar dependencias
pip install -r requirements.txt
```

---

## 2. Aplicación de Migraciones de Base de Datos (Principio VI)

Ejecuta la migración que agrega `priority` y `category_id` a `tasks`, y crea la tabla `categories`:

```powershell
flask db upgrade
```

---

## 3. Ejecución de Pruebas Automatizadas (Principio IV)

Ejecuta la suite con especial atención en las pruebas bloqueantes de prioridad, desvinculación sin cascada y vencimiento:

```powershell
# 1. Pruebas de dominio y servicios (Test-First)
pytest tests/services/test_task_service.py tests/services/test_category_service.py -v

# 2. Pruebas de integración HTTP
pytest tests/functional/ -v

# 3. Suite completa
pytest -v
```

---

## 4. Verificación de Escenarios E2E

Inicia la aplicación:
```powershell
flask run
```

### Escenario A: Prioridad y Ordenamiento (HU-07)
1. Crea una tarea sin indicar prioridad: verifica que se le asigne automáticamente "media" (`medium`).
2. Crea una segunda tarea con prioridad "alta" y una tercera con prioridad "baja".
3. En la interfaz, aplica la opción de ordenar por **Prioridad (Alta a Baja)**.
4. **Verificación**: Las tareas se reordenan mostrando primero la de prioridad alta, luego la de prioridad media y al final la de prioridad baja.
5. Cambia la prioridad de la tercera tarea a "alta": el ordenamiento se actualiza inmediatamente.

### Escenario B: Categorías y Desvinculación sin Cascada (HU-08)
1. Accede a la sección de categorías y crea una categoría llamada "Universidad".
2. Asigna 2 tareas existentes a la categoría "Universidad".
3. Filtra el listado por categoría "Universidad": comprueba que solo se muestren esas 2 tareas.
4. Elimina la categoría "Universidad".
5. **Verificación Crítica de Integridad**:
   - Vuelve al listado general de tareas: comprueba que las 2 tareas siguen existiendo y visibles.
   - Ambas tareas ahora figuran como "Sin categoría" (`category_id = NULL`).
   - Ninguna tarea fue eliminada.

### Escenario C: Indicador de Vencimiento en Backend (HU-09)
1. Crea una tarea con fecha límite de ayer y estado "pendiente": comprueba que aparece visualmente resaltada como **Vencida** (`is_overdue = true`).
2. Marca esa misma tarea como "completada":
   - **Verificación**: Inmediatamente el indicador de "Vencida" desaparece (`is_overdue = false`), ya que una tarea completada nunca se considera vencida.
3. Crea una tarea con fecha límite de mañana y estado "pendiente": comprueba que NO figura como vencida.
