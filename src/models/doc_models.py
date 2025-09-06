"""Модели для документации 1С."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Типы документации 1С."""
    GLOBAL_FUNCTION = "global_function"
    GLOBAL_PROCEDURE = "global_procedure"
    GLOBAL_EVENT = "global_event"
    OBJECT_FUNCTION = "object_function"
    OBJECT_PROCEDURE = "object_procedure"
    OBJECT_PROPERTY = "object_property"
    OBJECT_EVENT = "object_event"
    OBJECT_CONSTRUCTOR = "object_constructor"
    OBJECT = "object"


class ObjectMethod(BaseModel):
    """Метод объекта."""
    name: str
    name_en: str = ""
    href: str = ""
    
    
class ObjectProperty(BaseModel):
    """Свойство объекта."""
    name: str
    name_en: str = ""
    href: str = ""


class ObjectEvent(BaseModel):
    """Событие объекта."""
    name: str
    name_en: str = ""
    href: str = ""


class Parameter(BaseModel):
    """Параметр функции/метода."""
    name: str
    type: str
    description: str = ""
    required: bool = True


class Documentation(BaseModel):
    """Базовая модель документации."""
    id: str = Field(..., description="Уникальный идентификатор")
    type: DocumentType
    name: str
    object: Optional[str] = None  # Для методов/свойств/событий объектов
    syntax_ru: str = ""
    syntax_en: str = ""
    description: str = ""
    parameters: List[Parameter] = []
    return_type: Optional[str] = None
    usage: Optional[str] = None  # Для свойств - "Чтение и запись", "Только чтение" и т.д.
    version_from: Optional[str] = None
    examples: List[str] = []
    source_file: str = ""
    full_path: str = ""  # Полный путь типа "ТаблицаЗначений.Добавить"
    
    # Для объектов - списки методов, свойств и событий
    methods: List[ObjectMethod] = []
    properties: List[ObjectProperty] = []
    events: List[ObjectEvent] = []
    
    def __post_init__(self):
        """Автоматически заполняет full_path и id."""
        if self.object:
            self.full_path = f"{self.object}.{self.name}"
            self.id = f"{self.object}_{self.name}_{self.type.value}"
        else:
            self.full_path = self.name
            self.id = f"{self.name}_{self.type.value}"


class HBKFile(BaseModel):
    """Информация о .hbk файле."""
    path: str
    size: int
    modified: float
    entries_count: int = 0


class HBKEntry(BaseModel):
    """Запись в .hbk архиве."""
    path: str
    size: int
    is_dir: bool
    content: Optional[bytes] = None


class CategoryInfo(BaseModel):
    """Информация из файла __categories__."""
    name: str = ""
    description: str = ""
    version_from: Optional[str] = None
    section: str = ""


class ParsedHBK(BaseModel):
    """Результат парсинга .hbk файла."""
    file_info: HBKFile
    categories: Dict[str, CategoryInfo] = {}
    documentation: List[Documentation] = []
    errors: List[str] = []
    stats: Dict[str, int] = {}
