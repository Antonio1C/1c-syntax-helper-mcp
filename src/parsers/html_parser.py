"""Парсер HTML документации 1С."""

import re
from typing import Optional
from bs4 import BeautifulSoup

from src.models.doc_models import Documentation, Parameter, DocumentType, ObjectMethod, ObjectProperty, ObjectEvent
from src.core.logging import get_logger

logger = get_logger(__name__)


class HTMLParser:
    """Парсер HTML документации 1С."""
    
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
            
            # Для объектов переопределяем object из заголовка
            if doc.type == DocumentType.OBJECT:
                doc.object = self._extract_object_name_from_title(soup)
            elif doc.type == DocumentType.OBJECT_PROPERTY:
                # Для свойств объектов также переопределяем object
                doc.object = self._extract_object_name_from_title(soup)
                # И извлекаем информацию об использовании
                self._extract_usage(soup, doc)
            elif doc.type == DocumentType.OBJECT_EVENT:
                # Для событий объектов также переопределяем object
                doc.object = self._extract_object_name_from_title(soup)
            
            # Для объектов извлекаем методы, свойства и события
            if doc.type == DocumentType.OBJECT:
                self._extract_object_methods(soup, doc)
                self._extract_object_properties(soup, doc)
                self._extract_object_events(soup, doc)
            else:
                # Для функций/методов/событий извлекаем синтаксис, параметры и примеры
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
            
        # Для пути objects/catalog125/catalog462/object464.html
        # нужно взять последний каталог перед HTML файлом
        if objects_idx + 1 < len(parts):
            # Ищем последний каталог перед HTML файлом
            for i in range(len(parts) - 2, objects_idx, -1):  # Идем от конца к началу
                part = parts[i]
                if not part.endswith('.html') and part.startswith('catalog'):
                    return part
            
            # Если не найден каталог, берем первый элемент после objects
            object_part = parts[objects_idx + 1]
            if not object_part.endswith('.html'):
                return object_part
                
        return None
    
    def _is_function_not_procedure(self, soup: BeautifulSoup) -> bool:
        """Определяет, является ли метод функцией (возвращает значение) или процедурой."""
        # Ищем заголовок "Возвращаемое значение" в V8SH_chapter
        chapter_headers = soup.find_all('p', class_='V8SH_chapter')
        for header in chapter_headers:
            header_text = header.get_text(strip=True).lower()
            if 'возвращаемое' in header_text or 'return' in header_text:
                return True
        
        # По умолчанию считаем процедурой
        return False
    
    def _extract_object_name_from_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Извлекает имя объекта из заголовка для объектов."""
        # Ищем заголовок в V8SH_pagetitle или V8SH_heading
        title_tag = soup.find('h1', class_='V8SH_pagetitle') or soup.find('p', class_='V8SH_heading')
        if not title_tag:
            return None
            
        title_text = title_tag.get_text(strip=True)
        if not title_text:
            return None
            
        # Убираем английскую часть в скобках
        if ' (' in title_text:
            title_text = title_text.split(' (')[0]
        
        # Для объектов: "РегистрБухгалтерииМенеджер.<Имя регистра бухгалтерии>"
        # Для событий: "КритерийОтбораМенеджер.<Имя критерия>.ОбработкаПолученияФормы"
        
        if '.' in title_text:
            parts = title_text.split('.')
            if len(parts) == 2:
                # Обычный объект: "РегистрБухгалтерииМенеджер.<Имя регистра бухгалтерии>"
                return parts[0].strip()
            elif len(parts) > 2:
                # Событие/метод: "КритерийОтбораМенеджер.<Имя критерия>.ОбработкаПолученияФормы"
                # Объектом является все кроме последней части
                return '.'.join(parts[:-1]).strip()
            else:
                return parts[0].strip()
            
        return title_text.strip()
    
    def _extract_usage(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает информацию об использовании для свойств."""
        # Получаем HTML контент после заголовка "Использование"
        usage_content = self._get_content_after_chapter(soup, ['использование'])
        if not usage_content:
            return
            
        # Извлекаем текст из HTML
        from bs4 import BeautifulSoup as BS
        clean_usage = BS(usage_content, 'html.parser').get_text()
        doc.usage = clean_usage.strip()
    
    def _get_content_after_chapter(self, soup: BeautifulSoup, chapter_keywords: list) -> str:
        """
        Универсальный метод для получения HTML контента после заголовка V8SH_chapter.
        
        Args:
            soup: Объект BeautifulSoup
            chapter_keywords: Список ключевых слов для поиска заголовка (в нижнем регистре)
            
        Returns:
            HTML строка с контентом после найденного заголовка до следующего заголовка
        """
        chapter_headers = soup.find_all('p', class_='V8SH_chapter')
        
        for header in chapter_headers:
            header_text = header.get_text(strip=True).lower()
            if any(keyword in header_text for keyword in chapter_keywords):
                parent = header.parent
                if parent:
                    header_html = str(header)
                    parent_html = str(parent)
                    
                    # Ищем позицию заголовка в родительском элементе
                    header_pos = parent_html.find(header_html)
                    if header_pos != -1:
                        # Берем HTML после заголовка
                        remaining_html = parent_html[header_pos + len(header_html):]
                        
                        # Ограничиваем до следующего заголовка V8SH_chapter
                        next_chapter_pos = remaining_html.find('class="V8SH_chapter"')
                        if next_chapter_pos != -1:
                            remaining_html = remaining_html[:next_chapter_pos]
                        
                        return remaining_html
                break
        
        return ""
    
    def _extract_title_and_description(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает заголовок и описание."""
        # Ищем заголовок в V8SH_pagetitle или V8SH_heading
        title_tag = soup.find('h1', class_='V8SH_pagetitle') or soup.find('p', class_='V8SH_heading')
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            if title_text:
                if doc.type == DocumentType.OBJECT:
                    # Для объектов берем часть после точки как имя
                    # Убираем английскую часть в скобках
                    if ' (' in title_text:
                        title_text = title_text.split(' (')[0].strip()
                    
                    if '.' in title_text:
                        # Извлекаем часть после точки как имя объекта
                        doc.name = title_text.split('.', 1)[1].strip()
                    else:
                        doc.name = title_text
                else:
                    # Для функций/методов/событий
                    if '.' in title_text:
                        # Разделяем русскую и английскую части
                        russian_part = title_text.split(' (')[0] if ' (' in title_text else title_text
                        english_part = title_text.split(' (')[1] if ' (' in title_text else ''
                        
                        # Берем последнюю часть русского названия
                        russian_parts = russian_part.split('.')
                        russian_name = russian_parts[-1] if len(russian_parts) > 1 else russian_part
                        
                        # Берем последнюю часть английского названия
                        if english_part:
                            english_parts = english_part.replace(')', '').split('.')
                            english_name = english_parts[-1] if len(english_parts) > 1 else english_part.replace(')', '')
                            doc.name = f"{russian_name} ({english_name})"
                        else:
                            doc.name = russian_name
                    else:
                        doc.name = title_text

        # Ищем описание в разделе "Описание:"
        desc_headers = soup.find_all('p', class_='V8SH_chapter')
        
        for header in desc_headers:
            header_text = header.get_text(strip=True).lower()
            if 'описание' in header_text or 'description' in header_text:
                # Ищем в тексте после заголовка до следующего V8SH_chapter
                description_parts = []
                elem = header.next_sibling
                
                while elem:
                    # Если нашли следующий заголовок - прерываем
                    if (hasattr(elem, 'get') and hasattr(elem, 'get_text') and 
                        elem.get('class') == ['V8SH_chapter']):
                        break
                    
                    if hasattr(elem, 'get_text'):
                        text = elem.get_text(strip=True)
                        if text and len(text) > 3:  # Игнорируем короткие фрагменты
                            description_parts.append(text)
                    elif isinstance(elem, str):
                        text = elem.strip()
                        if text and len(text) > 3:
                            description_parts.append(text)
                    
                    elem = elem.next_sibling
                
                if description_parts:
                    doc.description = ' '.join(description_parts)
                    break
    
    def _extract_syntax(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает синтаксис вызова."""
        # Ищем заголовок "Синтаксис:" с классом V8SH_chapter  
        chapter_headers = soup.find_all('p', class_='V8SH_chapter')
        
        for header in chapter_headers:
            header_text = header.get_text(strip=True).lower()
            if 'синтаксис' in header_text or 'syntax' in header_text:
                # Проверяем следующий элемент после заголовка
                next_elem = header.next_sibling
                if next_elem:
                    syntax_text = next_elem.get_text(strip=True) if hasattr(next_elem, 'get_text') else str(next_elem).strip()
                    if '(' in syntax_text and syntax_text:
                        doc.syntax_ru = syntax_text
                        return
                
                # Альтернативный поиск в тексте после заголовка
                remaining_text = ""
                elem = header.next_sibling
                while elem and not (hasattr(elem, 'get') and hasattr(elem, 'get_text') and elem.get('class') == ['V8SH_chapter']):
                    if hasattr(elem, 'get_text'):
                        remaining_text += elem.get_text(strip=True) + " "
                    elif isinstance(elem, str):
                        remaining_text += elem.strip() + " "
                    elem = elem.next_sibling
                
                # Ищем синтаксис в собранном тексте
                lines = remaining_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if '(' in line and ')' in line and len(line) < 200:
                        doc.syntax_ru = line
                        return
                break
    
    def _extract_parameters(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает параметры функции."""
        # Получаем HTML контент после заголовка "Параметры"
        remaining_html = self._get_content_after_chapter(soup, ['параметр', 'parameter'])
        
        if remaining_html:
            # Ищем блоки V8SH_rubric с параметрами
            # Первый паттерн - с информацией об обязательности: &lt;Строка&gt; (обязательный)
            rubric_pattern_with_required = r'<div class="V8SH_rubric"[^>]*>.*?&lt;([^&]+)&gt;\s*\(([^)]+)\).*?</div>(.*?)(?=<[^>]+class="V8SH_|$)'
            matches_with_required = re.findall(rubric_pattern_with_required, remaining_html, re.DOTALL)
            
            # Второй паттерн - без информации об обязательности: &lt;ВидФормы&gt;
            rubric_pattern_simple = r'<div class="V8SH_rubric"[^>]*>.*?&lt;([^&]+)&gt;[^(]*?</div>(.*?)(?=<[^>]+class="V8SH_|$)'
            matches_simple = re.findall(rubric_pattern_simple, remaining_html, re.DOTALL)
            
            # Обрабатываем параметры с информацией об обязательности
            for param_name, param_required, param_info in matches_with_required:
                self._process_parameter(doc, param_name, param_info, param_required)
            
            # Обрабатываем параметры без информации об обязательности
            for param_name, param_info in matches_simple:
                # Проверяем, что этот параметр еще не был добавлен
                if not any(p.name == param_name for p in doc.parameters):
                    self._process_parameter(doc, param_name, param_info, "")
    
    def _process_parameter(self, doc: Documentation, param_name: str, param_info: str, param_required: str):
        """Обрабатывает отдельный параметр."""
        # Извлекаем тип из ссылки на def_
        param_type = "Произвольный"
        type_match = re.search(r'<a\s+href="[^"]*def_[^"]*"[^>]*>([^<]+)</a>', param_info)
        if type_match:
            param_type = type_match.group(1).strip()
        
        # Извлекаем полное описание (весь текст после типа)
        # Удаляем HTML теги и получаем чистый текст
        from bs4 import BeautifulSoup as BS
        clean_info = BS(param_info, 'html.parser').get_text()
        
        # Убираем начальную часть "Тип: [тип]."
        param_desc = re.sub(r'^Тип:\s*[^.]+\.\s*', '', clean_info.strip())
        
        # Добавляем информацию об обязательности
        required_info = param_required.strip()
        if required_info:
            param_desc = f"({required_info}) {param_desc}"
        
        if param_name:
            param = Parameter(
                name=param_name,
                type=param_type,
                description=param_desc.strip()
            )
            doc.parameters.append(param)
    
    def _extract_return_type(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает тип и описание возвращаемого значения."""
        # Получаем HTML контент после заголовка "Возвращаемое значение"
        remaining_html = self._get_content_after_chapter(soup, ['возвращаемое', 'return'])
        
        if remaining_html:
            # Извлекаем полное описание возвращаемого значения
            from bs4 import BeautifulSoup as BS
            clean_info = BS(remaining_html, 'html.parser').get_text()
            
            # Ищем тип в ссылках на def_
            type_pattern = r'<a\s+href="[^"]*def_[^"]*"[^>]*>([^<]+)</a>'
            type_matches = re.findall(type_pattern, remaining_html)
            
            if type_matches:
                # Берем первый найденный тип как основной
                doc.return_type = type_matches[0].strip()
                
                # Добавляем полное описание
                clean_desc = re.sub(r'Тип:\s*[^.]+\.\s*', '', clean_info.strip())
                if clean_desc:
                    doc.return_type = f"{doc.return_type}. {clean_desc}"
            else:
                # Если тип не найден, используем весь текст как описание
                doc.return_type = clean_info.strip()
    
    def _extract_examples(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает примеры кода."""
        # Ищем заголовок "Пример:" с классом V8SH_chapter
        example_headers = soup.find_all('p', class_='V8SH_chapter')
        
        for header in example_headers:
            header_text = header.get_text(strip=True).lower()
            if 'пример' not in header_text and 'example' not in header_text:
                continue
                
            # Ищем таблицы с кодом после заголовка
            elem = header.next_sibling
            while elem:
                # Если нашли следующий заголовок - прерываем
                if (hasattr(elem, 'get') and hasattr(elem, 'get_text') and 
                    elem.get('class') == ['V8SH_chapter']):
                    break
                
                # Пропускаем текстовые узлы и элементы без методов find
                if not (hasattr(elem, 'name') and elem.name and hasattr(elem, 'find')):
                    elem = elem.next_sibling
                    continue
                
                tables = elem.find_all('table') if elem.name != 'table' else [elem]
                for table in tables:
                    # Ищем ячейки с кодом (обычно с моноширинным шрифтом)
                    code_cells = table.find_all('td')
                    for cell in code_cells:
                        fonts = cell.find_all('font', face='Courier New')
                        if not fonts:
                            continue
                            
                        # Получаем весь HTML внутри ячейки для корректного извлечения
                        cell_html = str(cell)
                        
                        # Извлекаем код, сохраняя структуру и переносы строк
                        from bs4 import BeautifulSoup as BS
                        cell_soup = BS(cell_html, 'html.parser')
                        
                        # Получаем текст, заменяя <BR> на переносы строк
                        for br in cell_soup.find_all('br'):
                            br.replace_with('\n')
                        
                        code_text = cell_soup.get_text()
                        
                        if code_text.strip() and len(code_text.strip()) > 5:
                            # Очищаем лишние пробелы, но сохраняем структуру
                            lines = code_text.split('\n')
                            clean_lines = [line.rstrip() for line in lines if line.strip()]
                            full_code = '\n'.join(clean_lines)
                            
                            if full_code.strip():
                                doc.examples.append(full_code.strip())
                
                elem = elem.next_sibling
            break
    
    def _extract_version(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает информацию о версии."""
        # Ищем элементы с классом V8SH_versionInfo
        version_elements = soup.find_all('p', class_='V8SH_versionInfo')
        
        for elem in version_elements:
            version_text = elem.get_text(strip=True)
            
            # Ищем версию типа "8.3.24" или "8.0"
            version_match = re.search(r'8\.\d+(?:\.\d+)?', version_text)
            if version_match:
                version = version_match.group(0)
                
                # Определяем тип версии по контексту
                if 'доступен' in version_text.lower() or 'начиная' in version_text.lower():
                    doc.version_from = version
                elif 'изменен' in version_text.lower() or 'описание' in version_text.lower():
                    # Это версия изменения, можно сохранить как дополнительную информацию
                    if not doc.version_from:
                        doc.version_from = version
    
    def _extract_object_methods(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает методы объекта."""
        # Ищем секцию "Методы:"
        methods_section = self._get_content_after_chapter(soup, ['методы'])
        if not methods_section:
            return
            
        # Ищем все ссылки на методы
        method_links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', methods_section)
        for href, name in method_links:
            # Парсим название (может быть "Выбрать (Select)")
            if '(' in name and ')' in name:
                match = re.match(r'([^(]+)\s*\(([^)]+)\)', name)
                if match:
                    name_ru = match.group(1).strip()
                    name_en = match.group(2).strip()
                else:
                    name_ru = name
                    name_en = ""
            else:
                name_ru = name
                name_en = ""
            
            method = ObjectMethod(
                name=name_ru,
                name_en=name_en,
                href=href
            )
            doc.methods.append(method)
    
    def _extract_object_properties(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает свойства объекта."""
        # Ищем секцию "Свойства:"
        properties_section = self._get_content_after_chapter(soup, ['свойства'])
        if not properties_section:
            return
            
        # Ищем все ссылки на свойства
        prop_links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', properties_section)
        for href, name in prop_links:
            # Парсим название
            if '(' in name and ')' in name:
                match = re.match(r'([^(]+)\s*\(([^)]+)\)', name)
                if match:
                    name_ru = match.group(1).strip()
                    name_en = match.group(2).strip()
                else:
                    name_ru = name
                    name_en = ""
            else:
                name_ru = name
                name_en = ""
            
            prop = ObjectProperty(
                name=name_ru,
                name_en=name_en,
                href=href
            )
            doc.properties.append(prop)
    
    def _extract_object_events(self, soup: BeautifulSoup, doc: Documentation):
        """Извлекает события объекта."""
        # Ищем секцию "События:"
        events_section = self._get_content_after_chapter(soup, ['события'])
        if not events_section:
            return
            
        # Ищем все ссылки на события
        event_links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', events_section)
        for href, name in event_links:
            # Парсим название
            if '(' in name and ')' in name:
                match = re.match(r'([^(]+)\s*\(([^)]+)\)', name)
                if match:
                    name_ru = match.group(1).strip()
                    name_en = match.group(2).strip()
                else:
                    name_ru = name
                    name_en = ""
            else:
                name_ru = name
                name_en = ""
            
            event = ObjectEvent(
                name=name_ru,
                name_en=name_en,
                href=href
            )
            doc.events.append(event)