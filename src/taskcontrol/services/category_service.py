from src.taskcontrol.extensions import db
from src.taskcontrol.models.audit import AuditLog
from src.taskcontrol.models.category import Category
from src.taskcontrol.models.task import Task
from src.taskcontrol.services.audit_service import AuditService


class CategoryValidationError(Exception):
    """Error de validación en los datos de una categoría."""
    pass


class DuplicateCategoryNameError(Exception):
    """El usuario ya tiene una categoría registrada con ese nombre."""
    pass


class CategoryNotFoundError(Exception):
    """Categoría inexistente o perteneciente a otro usuario."""
    pass


class CategoryService:
    """Lógica de negocio para categorías o proyectos del usuario (HU-08, Principio II)."""

    MAX_NAME_LENGTH = 50

    @classmethod
    def _normalizar_nombre(cls, name: str) -> str:
        """Valida y limpia el nombre de una categoría."""
        if not name or not name.strip():
            raise CategoryValidationError("El nombre de la categoría es obligatorio")

        limpio = name.strip()
        if len(limpio) > cls.MAX_NAME_LENGTH:
            raise CategoryValidationError(
                f"El nombre no puede exceder {cls.MAX_NAME_LENGTH} caracteres"
            )
        return limpio

    @classmethod
    def _existe_nombre(cls, user_id: int, nombre: str, excluir_id: int = None) -> bool:
        """Comprueba la unicidad del nombre ignorando mayúsculas y minúsculas.

        La `UniqueConstraint(user_id, name)` de la base de datos distingue mayúsculas,
        así que por sí sola dejaría convivir "Trabajo" y "trabajo". La especificación
        exige que se consideren duplicados, de ahí esta verificación explícita.
        """
        consulta = Category.query.filter(
            Category.user_id == user_id,
            db.func.lower(Category.name) == nombre.lower(),
        )
        if excluir_id is not None:
            consulta = consulta.filter(Category.id != excluir_id)
        return consulta.first() is not None

    @classmethod
    def get_category_by_id(cls, category_id: int, user_id: int) -> Category:
        """Obtiene una categoría verificando que pertenezca al usuario (Principio VII)."""
        categoria = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not categoria:
            raise CategoryNotFoundError("Categoría no encontrada")
        return categoria

    @classmethod
    def create_category(
        cls, user_id: int, name: str, description: str = None, color: str = None
    ) -> Category:
        """Crea una categoría para el usuario autenticado (HU-08)."""
        nombre = cls._normalizar_nombre(name)

        if cls._existe_nombre(user_id, nombre):
            raise DuplicateCategoryNameError(
                f"Ya tienes una categoría registrada con el nombre '{nombre}'"
            )

        categoria = Category(
            user_id=user_id,
            name=nombre,
            description=description.strip() if description else None,
            color=color.strip() if color else None,
        )
        db.session.add(categoria)
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action=AuditLog.ACTION_CATEGORY_CREATED,
            entity_id=categoria.id,
            details={"name": nombre, "color": categoria.color},
        )
        db.session.commit()

        return categoria

    @classmethod
    def get_user_categories(cls, user_id: int) -> list:
        """Lista las categorías del usuario con el conteo de tareas activas."""
        categorias = (
            Category.query.filter_by(user_id=user_id).order_by(Category.name.asc()).all()
        )

        resultado = []
        for categoria in categorias:
            # Solo cuentan las tareas vigentes: las eliminadas lógicamente no suman.
            conteo = Task.query.filter_by(
                category_id=categoria.id, is_deleted=False
            ).count()
            resultado.append(categoria.to_dict(task_count=conteo))
        return resultado

    @classmethod
    def update_category(
        cls, category_id: int, user_id: int, name: str, description: str = None, color: str = None
    ) -> Category:
        """Edita el nombre y los metadatos de una categoría propia (FR-007)."""
        categoria = cls.get_category_by_id(category_id=category_id, user_id=user_id)
        nombre = cls._normalizar_nombre(name)

        if cls._existe_nombre(user_id, nombre, excluir_id=categoria.id):
            raise DuplicateCategoryNameError(
                f"Ya tienes una categoría registrada con el nombre '{nombre}'"
            )

        categoria.name = nombre
        categoria.description = description.strip() if description else None
        categoria.color = color.strip() if color else None
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action=AuditLog.ACTION_CATEGORY_UPDATED,
            entity_id=categoria.id,
            details={"name": nombre, "color": categoria.color},
        )
        db.session.commit()

        return categoria

    @classmethod
    def delete_category(cls, category_id: int, user_id: int) -> dict:
        """Elimina una categoría desvinculando sus tareas, sin borrar ninguna (FR-009).

        Las tareas quedan con `category_id = NULL` y conservan toda su información
        y su historial de auditoría. No hay borrado en cascada bajo ninguna condición.
        """
        categoria = cls.get_category_by_id(category_id=category_id, user_id=user_id)

        tareas = Task.query.filter_by(category_id=categoria.id).all()
        for tarea in tareas:
            tarea.category_id = None

        nombre = categoria.name
        db.session.delete(categoria)
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action=AuditLog.ACTION_CATEGORY_DELETED,
            entity_id=category_id,
            details={"name": nombre, "tasks_unlinked_count": len(tareas)},
        )
        db.session.commit()

        return {"deleted_category_id": category_id, "tasks_unlinked_count": len(tareas)}
