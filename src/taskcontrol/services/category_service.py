import re
from src.taskcontrol.extensions import db
from src.taskcontrol.models.category import Category
from src.taskcontrol.models.task import Task
from src.taskcontrol.services.audit_service import AuditService

COLOR_REGEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class DuplicateCategoryNameError(Exception):
    """Ya existe una categoría con ese nombre para este usuario."""
    pass


class CategoryNotFoundError(Exception):
    """Categoría no encontrada o no perteneciente al usuario."""
    pass


class InvalidCategoryColorError(Exception):
    """El color no cumple el formato hexadecimal estricto #RRGGBB."""
    pass


class CategoryService:
    """Lógica de negocio para categorías/proyectos de organización de tareas (Principio II)."""

    @classmethod
    def _validate_color(cls, color: str):
        if color and not COLOR_REGEX.match(color):
            raise InvalidCategoryColorError(
                "El color debe tener el formato hexadecimal #RRGGBB"
            )

    @classmethod
    def _assert_name_available(cls, user_id: int, name: str, exclude_category_id: int = None):
        clean_name = name.strip()
        query = Category.query.filter(
            Category.user_id == user_id, db.func.lower(Category.name) == clean_name.lower()
        )
        if exclude_category_id is not None:
            query = query.filter(Category.id != exclude_category_id)
        if query.first():
            raise DuplicateCategoryNameError(
                f"Ya tienes una categoría registrada con el nombre '{clean_name}'"
            )

    @classmethod
    def create_category(
        cls, user_id: int, name: str, description: str = None, color: str = None
    ) -> Category:
        """Crea una nueva categoría personal y audita el evento."""
        clean_name = (name or "").strip()
        cls._assert_name_available(user_id=user_id, name=clean_name)
        cls._validate_color(color)

        category = Category(
            user_id=user_id,
            name=clean_name,
            description=description.strip() if description else None,
            color=color or None,
        )
        db.session.add(category)
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="CATEGORY_CREATED",
            entity_id=category.id,
            details={"name": clean_name},
        )
        db.session.commit()

        return category

    @classmethod
    def get_category_by_id(cls, user_id: int, category_id: int) -> Category:
        """Obtiene una categoría verificando la propiedad del usuario autenticado."""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            raise CategoryNotFoundError("Categoría no encontrada")
        return category

    @classmethod
    def list_user_categories(cls, user_id: int) -> list:
        """Lista las categorías del usuario con el conteo de tareas activas por categoría."""
        categories = Category.query.filter_by(user_id=user_id).order_by(Category.name.asc()).all()
        result = []
        for category in categories:
            task_count = Task.query.filter_by(
                category_id=category.id, is_deleted=False
            ).count()
            result.append(category.to_dict(task_count=task_count))
        return result

    @classmethod
    def update_category(
        cls,
        category_id: int,
        user_id: int,
        name: str,
        description: str = None,
        color: str = None,
    ) -> Category:
        """Edita nombre, descripción y/o color de una categoría propia (HU-08, FR-007)."""
        category = cls.get_category_by_id(user_id=user_id, category_id=category_id)

        clean_name = (name or "").strip()
        cls._assert_name_available(
            user_id=user_id, name=clean_name, exclude_category_id=category.id
        )
        cls._validate_color(color)

        category.name = clean_name
        category.description = description.strip() if description else None
        category.color = color or None
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="CATEGORY_UPDATED",
            entity_id=category.id,
            details={"name": clean_name},
        )
        db.session.commit()

        return category

    @classmethod
    def delete_category(cls, category_id: int, user_id: int) -> int:
        """Elimina la categoría y desvincula (SET NULL) las tareas asociadas, sin borrarlas."""
        category = cls.get_category_by_id(user_id=user_id, category_id=category_id)

        tasks_unlinked = Task.query.filter_by(category_id=category.id).update(
            {Task.category_id: None}
        )
        db.session.delete(category)
        db.session.commit()

        AuditService.log_event(
            actor_id=user_id,
            action="CATEGORY_DELETED",
            entity_id=category_id,
            details={"tasks_unlinked_count": tasks_unlinked},
        )
        db.session.commit()

        return tasks_unlinked
