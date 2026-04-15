from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, cast

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from open_notebook.database.repository import ensure_record_id
from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
    NotFoundError,
)
from open_notebook.seekdb import seekdb_business_store

T = TypeVar("T", bound="ObjectModel")


class ObjectModel(BaseModel):
    id: Optional[str] = None
    table_name: ClassVar[str] = ""
    nullable_fields: ClassVar[set[str]] = set()  # Fields that can be saved as None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    @classmethod
    async def get_all(cls: Type[T], order_by=None) -> List[T]:
        try:
            # If called from a specific subclass, use its table_name
            if cls.table_name:
                target_class = cls
                table_name = cls.table_name
            else:
                # This path is taken if called directly from ObjectModel
                raise InvalidInputError(
                    "get_all() must be called from a specific model class"
                )
            result = await seekdb_business_store.list_entities(
                table_name, order_by=order_by
            )
            objects = []
            for obj in result:
                try:
                    objects.append(target_class(**obj))
                except Exception as e:
                    logger.critical(f"Error creating object: {str(e)}")

            return objects
        except Exception as e:
            logger.error(f"Error fetching all {cls.table_name}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @classmethod
    async def get(cls: Type[T], id: str) -> T:
        if not id:
            raise InvalidInputError("ID cannot be empty")
        try:
            # Get the table name from the ID (everything before the first colon)
            table_name = id.split(":")[0] if ":" in id else id

            # If we're calling from a specific subclass and IDs match, use that class
            if cls.table_name and cls.table_name == table_name:
                target_class: Type[T] = cls
            else:
                # Otherwise, find the appropriate subclass based on table_name
                found_class = cls._get_class_by_table_name(table_name)
                if not found_class:
                    raise InvalidInputError(f"No class found for table {table_name}")
                target_class = cast(Type[T], found_class)

            result = await seekdb_business_store.get_entity(ensure_record_id(id))
            if result:
                return target_class(**result)
            raise NotFoundError(f"{table_name} with id {id} not found")
        except Exception as e:
            logger.error(f"Error fetching object with id {id}: {str(e)}")
            logger.exception(e)
            raise NotFoundError(f"Object with id {id} not found - {str(e)}")

    @classmethod
    def _get_class_by_table_name(cls, table_name: str) -> Optional[Type["ObjectModel"]]:
        """Find the appropriate subclass based on table_name."""

        def get_all_subclasses(c: Type["ObjectModel"]) -> List[Type["ObjectModel"]]:
            all_subclasses: List[Type["ObjectModel"]] = []
            for subclass in c.__subclasses__():
                all_subclasses.append(subclass)
                all_subclasses.extend(get_all_subclasses(subclass))
            return all_subclasses

        for subclass in get_all_subclasses(ObjectModel):
            if hasattr(subclass, "table_name") and subclass.table_name == table_name:
                return subclass
        return None

    async def save(self) -> None:
        """
        Save the model to the database.

        Note: Embedding is no longer generated inline. Subclasses that need
        embedding should override save() to submit the appropriate embed_*
        command after calling super().save().
        """
        try:
            self.model_validate(self.model_dump(), strict=True)
            data = self._prepare_save_data()
            data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            db_result: Dict[str, Any]
            if self.id is None:
                data["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db_result = await seekdb_business_store.create_entity(self.__class__.table_name, data)
            else:
                data["created"] = (
                    self.created.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(self.created, datetime)
                    else self.created
                )
                logger.debug(f"Updating record with id {self.id}")
                db_result = await seekdb_business_store.update_entity(
                    self.__class__.table_name, self.id, data
                )
            # Update the current instance with the result
            for key, value in db_result.items():
                if hasattr(self, key):
                    if isinstance(getattr(self, key), BaseModel):
                        setattr(self, key, type(getattr(self, key))(**value))
                    else:
                        setattr(self, key, value)

        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise
        except RuntimeError:
            # Transaction conflicts should propagate for retry
            raise
        except Exception as e:
            logger.error(f"Error saving record: {e}")
            raise DatabaseOperationError(e)

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = self.model_dump()
        return {
            key: value
            for key, value in data.items()
            if value is not None or key in self.__class__.nullable_fields
        }

    async def delete(self) -> bool:
        if self.id is None:
            raise InvalidInputError("Cannot delete object without an ID")
        try:
            logger.debug(f"Deleting record with id {self.id}")
            return await seekdb_business_store.delete_entity(self.id)
        except Exception as e:
            logger.error(
                f"Error deleting {self.__class__.table_name} with id {self.id}: {str(e)}"
            )
            raise DatabaseOperationError(
                f"Failed to delete {self.__class__.table_name}"
            )

    async def relate(
        self, relationship: str, target_id: str, data: Optional[Dict] = {}
    ) -> Any:
        if not relationship or not target_id or not self.id:
            raise InvalidInputError("Relationship and target ID must be provided")
        try:
            return await seekdb_business_store.create_relation(
                relationship, source=self.id, target=target_id, data=data
            )
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class RecordModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra="allow",
        from_attributes=True,
        defer_build=True,
    )

    record_id: ClassVar[str]
    auto_save: ClassVar[bool] = (
        False  # Default to False, can be overridden in subclasses
    )
    _instances: ClassVar[Dict[str, "RecordModel"]] = {}  # Store instances by record_id

    def __new__(cls, **kwargs):
        # If an instance already exists for this record_id, return it
        if cls.record_id in cls._instances:
            instance = cls._instances[cls.record_id]
            # Update instance with any new kwargs if provided
            if kwargs:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
            return instance

        # If no instance exists, create a new one
        instance = super().__new__(cls)
        cls._instances[cls.record_id] = instance
        return instance

    def __init__(self, **kwargs):
        # Only initialize if this is a new instance
        if not hasattr(self, "_initialized"):
            object.__setattr__(self, "__dict__", {})

            # For RecordModel, we need to handle async initialization differently
            # Initialize with provided kwargs only for now
            super().__init__(**kwargs)

            # Mark as initialized but not loaded from DB yet
            object.__setattr__(self, "_initialized", True)
            object.__setattr__(self, "_db_loaded", False)

    async def _load_from_db(self):
        """Load data from database if not already loaded"""
        if not getattr(self, "_db_loaded", False):
            result = await seekdb_business_store.get_singleton(self.record_id)
            if result:
                for key, value in result.items():
                    if hasattr(self, key):
                        object.__setattr__(self, key, value)

            object.__setattr__(self, "_db_loaded", True)

    @classmethod
    async def get_instance(cls) -> "RecordModel":
        """Get or create the singleton instance and load from DB"""
        instance = cls()
        await instance._load_from_db()
        return instance

    @model_validator(mode="after")
    def auto_save_validator(self):
        if self.__class__.auto_save:
            # Auto-save can't work with async - log warning
            logger.warning(
                f"Auto-save is enabled for {self.__class__.__name__} but update() is now async. Call await instance.update() manually."
            )
        return self

    async def update(self):
        # Get all non-ClassVar fields and their values
        data = {
            field_name: getattr(self, field_name)
            for field_name, field_info in self.model_fields.items()
            if not str(field_info.annotation).startswith("typing.ClassVar")
        }

        result = await seekdb_business_store.upsert_singleton(self.record_id, data)
        if result:
            for key, value in result.items():
                if hasattr(self, key):
                    object.__setattr__(self, key, value)

        return self

    @classmethod
    def clear_instance(cls):
        """Clear the singleton instance (useful for testing)"""
        if cls.record_id in cls._instances:
            del cls._instances[cls.record_id]

    async def patch(self, model_dict: dict):
        """Update model attributes from dictionary and save"""
        for key, value in model_dict.items():
            setattr(self, key, value)
        await self.update()
