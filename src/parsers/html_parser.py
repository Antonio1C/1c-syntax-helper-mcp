"""Парсер HTML документации 1С."""

import re
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from src.models.doc_models import Documentation, Parameter, DocumentType
from src.core.logging import get_logger

logger = get_logger(__name__)


class HTMLParser:
    """Парсер HTML документации 1С."""
    
    def __init__(self):
        self.encoding = 'utf-8'
    
    def parse_html_content(self, content: bytes, file_path: str) -> Optional[Documentation]:
        """Парсит HTML содержимое и извлекает документацию."""
        try:
            # Декодируем содержимое
            html_content = self._decode_content(content)
            if not html_content:
                return None
            
            # Парсим HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Определяем тип документации из пути файла
            doc_type, object_name, item_name = self._parse_file_path(file_path)
            
            # Для методов определяем точный тип (функция/процедура) по содержимому
            if doc_type in [DocumentType.GLOBAL_FUNCTION, DocumentType.OBJECT_FUNCTION]:
                is_function = self._is_function_not_procedure(soup)
                if not is_function:
                    if doc_type == DocumentType.GLOBAL_FUNCTION:
                        doc_type = DocumentType.GLOBAL_PROCEDURE
                    else:
                        doc_type = DocumentType.OBJECT_PROCEDURE
            
            # Создаем базовый объект документации
            doc = Documentation(
                id="",  # Будет заполнен в __post_init__
                type=doc_type,
                name=item_name,
                object=object_name,
                source_file=file_path
            )
            
            # Извлекаем основную информацию
            self._extract_title_and_description(soup, doc)
            self._extract_syntax(soup, doc)
            self._extract_parameters(soup, doc)
            self._extract_return_type(soup, doc)
            self._extract_examples(soup, doc)
            self._extract_version(soup, doc)
            
            # Автоматически заполняем служебные поля
            doc.__post_init__()
            
            logger.debug(f"Обработан HTML файл: {file_path} -> {doc.name}")
            return doc
            
        except Exception as e:
            logger.error(f"Ошибка парсинга HTML файла {file_path}: {e}")
            return None
    
    def _decode_content(self, content: bytes) -> Optional[str]:
        """Декодирует содержимое файла в строку."""
        encodings = ['utf-8', 'windows-1251', 'cp1251', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        logger.warning("Не удалось декодировать содержимое файла")
        return None
    
    def _parse_file_path(self, file_path: str) -> tuple[DocumentType, Optional[str], str]:
        """Определяет тип документации из пути файла."""
        # Нормализуем путь
        path_str = file_path.replace('\\', '/')
        path_parts = path_str.split('/')
        
        # Убираем расширение из имени файла
        file_name = path_parts[-1]
        if file_name.endswith('.html'):
            file_name = file_name[:-5]
        
        # Ищем ключевые слова в пути
        path_lower = path_str.lower()
        
        if '/methods/' in path_lower:
            # Это метод (функция/процедура) - определяем тип по содержимому
            object_name = self._extract_object_name(path_str, 'methods')
            
            # TODO: Пока используем FUNCTION по умолчанию, позже добавим анализ содержимого
            # для различения функций и процедур
            if object_name and object_name.lower() == 'global context':
                return DocumentType.GLOBAL_FUNCTION, object_name, file_name
            else:
                return DocumentType.OBJECT_FUNCTION, object_name, file_name
            
        elif '/properties/' in path_lower:
            # Это свойство объекта (глобальных свойств в 1С нет)
            object_name = self._extract_object_name(path_str, 'properties')
            return DocumentType.OBJECT_PROPERTY, object_name, file_name
            
        elif '/events/' in path_lower:
            # Это событие - может быть глобальным или объектным
            object_name = self._extract_object_name(path_str, 'events')
            if object_name and object_name.lower() == 'global context':
                return DocumentType.GLOBAL_EVENT, object_name, file_name
            else:
                return DocumentType.OBJECT_EVENT, object_name, file_name
            
        elif '/ctors/' in path_lower or '/ctor/' in path_lower:
            # Это конструктор объекта
            object_name = self._extract_object_name(path_str, 'ctors')
            if not object_name:
                object_name = self._extract_object_name(path_str, 'ctor')
            return DocumentType.OBJECT_CONSTRUCTOR, object_name, file_name
            
        elif 'globalfunctions/' in path_lower or '/functions/' in path_lower:
            # Глобальная функция
            return DocumentType.GLOBAL_FUNCTION, None, file_name
            
        elif '/objects/' in path_lower or path_lower.startswith('objects/'):
            # Это объект
            object_name = self._extract_main_object_name(path_str)
            return DocumentType.OBJECT, object_name, file_name
        
        # По умолчанию считаем объектом
        return DocumentType.OBJECT, None, file_name
        
    def _extract_object_name(self, path_str: str, member_type: str) -> Optional[str]:
        """Извлекает имя объекта из пути для методов/свойств/событий."""
        parts = path_str.split('/')
        
        # Ищем индекс папки с типом (methods/properties/events)
        member_idx = None
        for i, part in enumerate(parts):
            if part.lower() == member_type:
                member_idx = i
                break
                
        if member_idx is None:
            return None
            
        # Объект находится перед папкой типа
        if member_idx > 0:
            object_part = parts[member_idx - 1]
            
            # Если это специальные объекты как "Global context"
            if object_part == "Global context":
                return "Global context"
            
            # Если это каталожная структура catalog123, извлекаем имя
            if object_part.startswith('catalog'):
                # Попробуем найти более читаемое имя объекта
                # Ищем в предыдущих частях пути
                for j in range(member_idx - 1, -1, -1):
                    if not parts[j].startswith('catalog') and parts[j] != 'objects':
                        return parts[j]
                        
            return object_part
            
        return None
        
    def _extract_main_object_name(self, path_str: str) -> Optional[str]:
        """Извлекает имя основного объекта из пути."""
        parts = path_str.split('/')
        
        # Ищем индекс папки objects
        objects_idx = None
        for i, part in enumerate(parts):
            if part.lower() == 'objects':
                objects_idx = i
                break
                
        if objects_idx is None:
            return None
            
        # Берем следующий элемент после objects
        if objects_idx + 1 < len(parts):
            object_part = parts[objects_idx + 1]
            
            # Если это не HTML файл, значит это имя объекта
            if not object_part.endswith('.html'):
                return object_part
                
        return None
    
    def _is_function_not_procedure(self, soup: BeautifulSoup) -> bool:
        """Определяет, является ли метод функцией (возвращает значение) или процедурой."""
        # Ищем информацию о возвращаемом значении
        return_indicators = [
            'возвращаемое значение',
            'return value', 
            'returns',
            'тип возвращаемого значения',
            'return type'
        ]
        
        text = soup.get_text().lower()
        
        # Если есть упоминание возвращаемого значения - это функция
        for indicator in return_indicators:
            if indicator in text:
                return True
                
        # Ищем в структурированных элементах
        # Типичные селекторы для возвращаемого значения
        return_selectors = [
            '.return-value',
            '.returns',
            '.return-type',
            'h3:contains("Возвращаемое значение")',
            'h4:contains("Return value")',
            'dt:contains("Возвращаемое")',
            'th:contains("Возвращаемое")'
        ]
        
        for selector in return_selectors:
            try:
                if soup.select(selector):
                    return True
            except:
                continue
                
        # По умолчанию считаем процедурой
        return False
    
    def _extract_title_and_description(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает заголовок и описание."""
        # Ищем заголовок
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text and not doc.name:
                doc.name = title_text
        
        # Ищем описание в различных местах
        description_selectors = [
            'div.description',
            'div.summary', 
            'p.description',
            '.content p:first-of-type',
            'body > p:first-of-type'
        ]
        
        for selector in description_selectors:
            desc_tag = soup.select_one(selector)
            if desc_tag:
                desc_text = desc_tag.get_text(strip=True)
                if desc_text and len(desc_text) > 10:
                    doc.description = desc_text
                    break
        
        # Если описание не найдено, берем первый абзац
        if not doc.description:
            first_p = soup.find('p')
            if first_p:
                doc.description = first_p.get_text(strip=True)
    
    def _extract_syntax(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает синтаксис вызова."""
        # Ищем блоки с синтаксисом
        syntax_selectors = [
            'div.syntax',
            'pre.syntax',
            'code.syntax',
            '.syntax-block',
            'pre:contains("(")',
            'code:contains("(")'
        ]
        
        for selector in syntax_selectors:
            syntax_tag = soup.select_one(selector)
            if syntax_tag:
                syntax_text = syntax_tag.get_text(strip=True)
                if '(' in syntax_text:
                    doc.syntax_ru = syntax_text
                    break
        
        # Если не найдено, ищем по ключевым словам
        if not doc.syntax_ru:
            all_text = soup.get_text()
            lines = all_text.split('\n')
            for line in lines:
                line = line.strip()
                if (doc.name in line and '(' in line and 
                    len(line) < 200 and not line.startswith('//')):
                    doc.syntax_ru = line
                    break
    
    def _extract_parameters(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает параметры функции."""
        # Ищем таблицы или списки с параметрами
        param_sections = soup.find_all(['table', 'dl', 'div'], 
                                     class_=re.compile(r'param|argument', re.I))
        
        for section in param_sections:
            if section.name == 'table':
                self._parse_parameter_table(section, doc)
            elif section.name == 'dl':
                self._parse_parameter_list(section, doc)
    
    def _parse_parameter_table(self, table: Tag, doc: Documentation):
        """Парсит таблицу с параметрами."""
        rows = table.find_all('tr')
        if len(rows) < 2:  # Нет данных, только заголовок
            return
        
        # Пропускаем заголовок
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                param_name = cells[0].get_text(strip=True)
                param_desc = cells[1].get_text(strip=True)
                param_type = cells[2].get_text(strip=True) if len(cells) > 2 else "Произвольный"
                
                if param_name:
                    param = Parameter(
                        name=param_name,
                        type=param_type,
                        description=param_desc
                    )
                    doc.parameters.append(param)
    
    def _parse_parameter_list(self, dl: Tag, doc: Documentation):
        """Парсит список определений с параметрами."""
        dt_tags = dl.find_all('dt')
        dd_tags = dl.find_all('dd')
        
        for i, dt in enumerate(dt_tags):
            param_name = dt.get_text(strip=True)
            param_desc = ""
            
            if i < len(dd_tags):
                param_desc = dd_tags[i].get_text(strip=True)
            
            if param_name:
                param = Parameter(
                    name=param_name,
                    type="Произвольный",
                    description=param_desc
                )
                doc.parameters.append(param)
    
    def _extract_return_type(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает тип возвращаемого значения."""
        # Ищем информацию о возвращаемом значении
        return_selectors = [
            '.return-type',
            '.returns', 
            'span:contains("Возвращаемое значение")',
            'strong:contains("Тип:")'
        ]
        
        for selector in return_selectors:
            return_tag = soup.select_one(selector)
            if return_tag:
                # Ищем тип в тексте
                text = return_tag.get_text(strip=True)
                if 'Строка' in text:
                    doc.return_type = "Строка"
                elif 'Число' in text:
                    doc.return_type = "Число"
                elif 'Булево' in text:
                    doc.return_type = "Булево"
                elif 'Дата' in text:
                    doc.return_type = "Дата"
                break
    
    def _extract_examples(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает примеры кода."""
        # Ищем блоки с примерами
        example_selectors = [
            'div.example',
            'pre.example',
            'code.example',
            '.code-block',
            'pre:contains("=")'
        ]
        
        for selector in example_selectors:
            example_tags = soup.select(selector)
            for tag in example_tags:
                example_text = tag.get_text(strip=True)
                if example_text and len(example_text) > 10:
                    doc.examples.append(example_text)
    
    def _extract_version(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает информацию о версии."""
        version_text = soup.get_text()
        
        # Ищем версию типа "8.3.24"
        version_match = re.search(r'8\.\d+\.\d+', version_text)
        if version_match:
            doc.version_from = version_match.group(0)
