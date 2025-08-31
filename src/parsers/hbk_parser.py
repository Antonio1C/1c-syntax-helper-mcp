
"""Парсер .hbk файлов (архивы документации 1С)."""

import os
import tempfile
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.models.doc_models import HBKFile, HBKEntry, ParsedHBK, CategoryInfo
from src.core.logging import get_logger
from src.parsers.html_parser import HTMLParser
from src.core.utils import (
    safe_subprocess_run, 
    SafeSubprocessError, 
    create_safe_temp_dir, 
    safe_remove_dir,
    validate_file_path
)
from src.core.constants import MAX_FILE_SIZE_MB, SUPPORTED_ENCODINGS

logger = get_logger(__name__)


class HBKParserError(Exception):
    """Исключение для ошибок парсера HBK."""
    pass


class HBKParser:
    """Парсер .hbk архивов с документацией 1С."""
    
    def __init__(self):
        self.supported_extensions = ['.hbk', '.zip', '.7z']
        self._zip_command = None
        self._archive_path = None
        self._max_file_size = MAX_FILE_SIZE_MB * 1024 * 1024  # MB в байты
        self.html_parser = HTMLParser()  # Инициализируем HTML парсер
    
    def parse_file(self, file_path: str) -> Optional[ParsedHBK]:
        """Парсит .hbk файл и извлекает содержимое."""
        file_path = Path(file_path)
        
        # Валидация входного файла
        try:
            validate_file_path(file_path, self.supported_extensions)
        except SafeSubprocessError as e:
            logger.error(f"Валидация файла не прошла: {e}")
            return None
        
        # Проверка размера файла
        if file_path.stat().st_size > self._max_file_size:
            logger.error(f"Файл слишком большой: {file_path.stat().st_size / 1024 / 1024:.1f}MB")
            return None
        
        logger.info(f"Начинаем парсинг файла: {file_path}")
        
        # Создаем объект результата
        result = ParsedHBK(
            file_info=HBKFile(
                path=str(file_path),
                size=file_path.stat().st_size,
                modified=file_path.stat().st_mtime
            )
        )
        
        try:
            # Пробуем разные методы извлечения
            entries = self._extract_archive(file_path)
            if not entries:
                result.errors.append("Не удалось извлечь файлы из архива")
                return result
            
            result.file_info.entries_count = len(entries)
            logger.info(f"Извлечено {len(entries)} записей из архива")
            
            # Анализируем структуру и извлекаем документацию
            self._analyze_structure(entries, result)
            
            logger.info(f"Парсинг завершен. Найдено документов: {len(result.documentation)}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка парсинга файла {file_path}: {e}")
            result.errors.append(f"Ошибка парсинга: {str(e)}")
            return result
    
    def _extract_archive(self, file_path: Path) -> List[HBKEntry]:
        """Извлекает содержимое архива через внешний 7zip."""
        try:
            entries = self._extract_external_7z(file_path)
            if entries:
                logger.info("Файл успешно обработан через внешний 7zip")
                return entries
            else:
                logger.error(f"Не удалось извлечь файлы из архива: {file_path}")
                return []
        except Exception as e:
            logger.error(f"Ошибка обработки архива через 7zip: {e}")
            return []
    
    def _analyze_structure(self, entries: List[HBKEntry], result: ParsedHBK):
        """Анализирует структуру архива и извлекает документацию."""
        
        # Статистика
        html_files = 0
        st_files = 0
        category_files = 0
        processed_html = 0  # Счетчик обработанных HTML файлов
        min_per_type = 3  # Минимум документов каждого типа
        max_files_per_batch = 10  # Максимум файлов за один проход
        
        # Целевые типы документации
        target_types = {
            'GLOBAL_FUNCTION': 0,
            'GLOBAL_PROCEDURE': 0, 
            'GLOBAL_EVENT': 0,
            'OBJECT_FUNCTION': 0,
            'OBJECT_PROCEDURE': 0,
            'OBJECT_PROPERTY': 0,
            'OBJECT_EVENT': 0,
            'OBJECT_CONSTRUCTOR': 0,
            'OBJECT': 0
        }
        
        # Группируем файлы по каталогам и типам
        global_methods_files = []
        global_events_files = []
        global_context_files = []
        object_constructors_files = []
        object_events_files = []
        other_object_files = []
        
        for entry in entries:
            if entry.is_dir:
                continue
                
            path_parts = entry.path.replace('\\', '/').split('/')
            
            # Анализируем файлы __categories__
            if path_parts[-1] == '__categories__':
                category_files += 1
                self._parse_categories_file(entry, result)
                continue
            
            # Собираем .html файлы по категориям
            if entry.path.endswith('.html'):
                html_files += 1
                
                # Глобальные методы (функции/процедуры)
                if ('objects/Global context/methods' in entry.path or 'objects\\Global context\\methods' in entry.path):
                    global_methods_files.append(entry)
                # Глобальные события
                elif ('objects/Global context/events' in entry.path or 'objects\\Global context\\events' in entry.path):
                    global_events_files.append(entry)
                # Другие файлы Global context (свойства)
                elif ('objects/Global context' in entry.path or 'objects\\Global context' in entry.path):
                    global_context_files.append(entry)
                # Конструкторы объектов
                elif ('/ctors/' in entry.path or '\\ctors\\' in entry.path or 
                      '/ctor/' in entry.path or '\\ctor\\' in entry.path):
                    object_constructors_files.append(entry)
                # События объектов (не Global context)
                elif (('/events/' in entry.path or '\\events\\' in entry.path) and 
                      'Global context' not in entry.path):
                    object_events_files.append(entry)
                # Файлы других объектов
                elif 'objects/' in entry.path or 'objects\\' in entry.path:
                    other_object_files.append(entry)
                continue
            
            # Анализируем .st файлы (шаблоны)
            if entry.path.endswith('.st'):
                st_files += 1
                continue
        
        logger.info(f"Распределение HTML файлов: методы={len(global_methods_files)}, события={len(global_events_files)}, "
                   f"Global context={len(global_context_files)}, конструкторы={len(object_constructors_files)}, "
                   f"события объектов={len(object_events_files)}, другие объекты={len(other_object_files)}")
        
        def check_found_types():
            """Проверяет, сколько документов каждого типа найдено."""
            for doc in result.documentation:
                doc_type = doc.type.name
                if doc_type in target_types:
                    target_types[doc_type] += 1
        
        def all_types_found():
            """Проверяет, найдены ли минимальные количества всех типов."""
            return all(count >= min_per_type for count in target_types.values())
        
        # Умная стратегия поиска: обрабатываем файлы пока не найдем все типы
        categories_processed = {
            'global_methods': 0,
            'global_events': 0, 
            'global_context': 0,
            'object_constructors': 0,
            'object_events': 0,
            'other_objects': 0
        }
        
        batch_size = 5  # Обрабатываем по 5 файлов из каждой категории за раз
        
        while not all_types_found() and processed_html < 100:  # Максимум 100 файлов всего
            initial_count = processed_html
            
            # 1. Обрабатываем глобальные методы
            for i in range(batch_size):
                if (categories_processed['global_methods'] + i < len(global_methods_files) and
                    (target_types['GLOBAL_FUNCTION'] < min_per_type or target_types['GLOBAL_PROCEDURE'] < min_per_type)):
                    entry = global_methods_files[categories_processed['global_methods'] + i]
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['global_methods'] += batch_size
            
            # 2. Обрабатываем глобальные события
            for i in range(batch_size):
                if (categories_processed['global_events'] + i < len(global_events_files) and
                    target_types['GLOBAL_EVENT'] < min_per_type):
                    entry = global_events_files[categories_processed['global_events'] + i]
                    logger.info(f"Обрабатываем файл события: {entry.path}")
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['global_events'] += batch_size
            
            # 3. Обрабатываем Global context (свойства)
            for i in range(batch_size):
                if (categories_processed['global_context'] + i < len(global_context_files) and
                    target_types['OBJECT_PROPERTY'] < min_per_type):
                    entry = global_context_files[categories_processed['global_context'] + i]
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['global_context'] += batch_size
            
            # 4. Обрабатываем конструкторы объектов (ищем OBJECT_CONSTRUCTOR)
            for i in range(batch_size):
                if (categories_processed['object_constructors'] + i < len(object_constructors_files) and
                    target_types['OBJECT_CONSTRUCTOR'] < min_per_type):
                    entry = object_constructors_files[categories_processed['object_constructors'] + i]
                    logger.info(f"Обрабатываем файл конструктора: {entry.path}")
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['object_constructors'] += batch_size
            
            # 5. Обрабатываем события объектов (ищем OBJECT_EVENT)
            for i in range(batch_size):
                if (categories_processed['object_events'] + i < len(object_events_files) and
                    target_types['OBJECT_EVENT'] < min_per_type):
                    entry = object_events_files[categories_processed['object_events'] + i]
                    logger.info(f"Обрабатываем файл события объекта: {entry.path}")
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['object_events'] += batch_size
            
            # 6. Обрабатываем другие объекты
            for i in range(batch_size):
                if (categories_processed['other_objects'] + i < len(other_object_files) and
                    (target_types['OBJECT_FUNCTION'] < min_per_type or 
                     target_types['OBJECT_PROCEDURE'] < min_per_type or
                     target_types['OBJECT'] < min_per_type)):
                    entry = other_object_files[categories_processed['other_objects'] + i]
                    self._create_document_from_html(entry, result)
                    processed_html += 1
            categories_processed['other_objects'] += batch_size
            
            # Обновляем счетчики найденных типов
            target_types = {key: 0 for key in target_types}  # Сбрасываем счетчики
            check_found_types()
            
            # Если за этот проход ничего не обработали, прерываем
            if processed_html == initial_count:
                break
        
        logger.info(f"Найдено типов документации: {target_types}")
        logger.info(f"Обработано по категориям: методы={categories_processed['global_methods']}, "
                   f"события={categories_processed['global_events']}, Global context={categories_processed['global_context']}, "
                   f"конструкторы={categories_processed['object_constructors']}, события объектов={categories_processed['object_events']}, "
                   f"другие объекты={categories_processed['other_objects']}")
        
        # Обновляем статистику
        result.stats = {
            'html_files': html_files,
            'global_methods_files': len(global_methods_files),
            'global_events_files': len(global_events_files), 
            'global_context_files': len(global_context_files),
            'object_constructors_files': len(object_constructors_files),
            'object_events_files': len(object_events_files),
            'other_object_files': len(other_object_files),
            'processed_html': processed_html,
            'categories_processed': categories_processed,
            'found_types': target_types,
            'st_files': st_files,
            'category_files': category_files,
            'total_entries': len(entries)
        }
        
        logger.info(f"Структура архива: HTML={html_files}, обработано {processed_html} по умной стратегии, ST={st_files}, Categories={category_files}")
    
    def _create_document_from_html(self, entry: HBKEntry, result: ParsedHBK):
        """Создает документ из HTML файла, используя HTMLParser для извлечения содержимого."""
        from src.models.doc_models import Documentation, DocumentType
        
        try:
            # Определяем имя документа из пути
            path_parts = entry.path.replace('\\', '/').split('/')
            doc_name = path_parts[-1].replace('.html', '')
            
            # Определяем категорию из пути
            category = path_parts[-2] if len(path_parts) > 1 else "common"
            
            # Извлекаем содержимое HTML файла из архива
            html_content = None
            if entry.content:
                # Если содержимое уже загружено
                html_content = entry.content
            else:
                # Извлекаем содержимое по требованию
                html_content = self.extract_file_content(entry.path)
            
            if not html_content:
                logger.warning(f"Не удалось извлечь содержимое файла {entry.path}")
                return
            
            # Парсим HTML используя HTMLParser
            documentation = self.html_parser.parse_html_content(
                content=html_content,
                file_path=entry.path
            )
            
            if documentation:
                # Добавляем обработанную документацию напрямую
                result.documentation.append(documentation)
                logger.debug(f"Создан документ: {documentation.name} из файла {entry.path}")
            else:
                logger.warning(f"HTMLParser не смог обработать файл {entry.path}")
            
        except Exception as e:
            logger.warning(f"Ошибка создания документа из {entry.path}: {e}")
    
    def _parse_categories_file(self, entry: HBKEntry, result: ParsedHBK):
        """Парсит файл __categories__ для извлечения метаинформации."""
        if not entry.content:
            return
        
        try:
            # Пробуем разные кодировки
            content = None
            for encoding in SUPPORTED_ENCODINGS:
                try:
                    content = entry.content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                logger.warning(f"Не удалось декодировать файл категорий {entry.path}")
                return
            
            # Создаем категорию
            path_parts = entry.path.replace('\\', '/').split('/')
            section_name = path_parts[-2] if len(path_parts) > 1 else "unknown"
            
            category = CategoryInfo(
                name=section_name,
                section=section_name,
                description=f"Раздел документации: {section_name}"
            )
            
            # Простой парсинг версии из содержимого
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if 'version' in line.lower() or 'версия' in line.lower():
                    # Ищем версию типа 8.3.24
                    version_match = re.search(r'8\.\d+\.\d+', line)
                    if version_match:
                        category.version_from = version_match.group(0)
                        break
            
            result.categories[section_name] = category
            logger.debug(f"Обработана категория: {section_name}")
            
        except Exception as e:
            logger.warning(f"Ошибка парсинга файла категорий {entry.path}: {e}")
    
    def _extract_external_7z(self, file_path: Path) -> List[HBKEntry]:
        """Извлекает список файлов из архива через внешний 7zip."""
        entries = []
        
        # Ищем доступный 7zip - сначала в PATH, затем в стандартных местах
        zip_commands = [
            '7z',           # В PATH
            '7z.exe',       # В PATH  
            '7za',          # В PATH (standalone версия)
            '7za.exe',      # В PATH (standalone версия)
            # Стандартные пути Windows
            'C:\\Program Files\\7-Zip\\7z.exe',
            'C:\\Program Files (x86)\\7-Zip\\7z.exe',
            # Переносная версия
            '7-Zip\\7z.exe',
            '7zip\\7z.exe'
        ]
        working_7z = None
        
        logger.info(f"Поиск 7zip для обработки файла: {file_path}")
        
        for cmd in zip_commands:
            try:
                logger.debug(f"Проверяем команду: {cmd}")
                result = safe_subprocess_run([cmd], timeout=5)
                # 7zip возвращает код 0 при показе help или содержит информацию о версии
                if result.returncode == 0 or 'Igor Pavlov' in result.stdout or '7-Zip' in result.stdout:
                    working_7z = cmd
                    logger.info(f"Найден рабочий 7zip: {cmd}")
                    break
            except SafeSubprocessError as e:
                logger.debug(f"Команда {cmd} не найдена: {e}")
                continue
        
        if not working_7z:
            logger.error("7zip не найден в системе. Проверьте установку 7-Zip")
            raise HBKParserError("7zip не найден в системе. Проверьте установку 7-Zip")
        
        # Получаем список файлов (без извлечения)
        logger.info(f"Получаем список файлов из архива: {file_path}")
        try:
            result = safe_subprocess_run([working_7z, 'l', str(file_path)], timeout=60)
        except SafeSubprocessError as e:
            logger.error(f"Ошибка выполнения команды 7zip: {e}")
            raise HBKParserError(f"Ошибка чтения архива: {e}")
        
        if result.returncode != 0:
            logger.error(f"7zip вернул код ошибки {result.returncode}: {result.stderr}")
            raise HBKParserError(f"Ошибка чтения архива: {result.stderr}")
        
        logger.debug(f"Вывод 7zip: {result.stdout[:500]}...")  # Первые 500 символов для отладки
        
        # Парсим вывод 7zip
        lines = result.stdout.split('\n')
        in_files_section = False
        
        for line in lines:
            if '---------------' in line:
                in_files_section = not in_files_section
                continue
            
            if in_files_section and line.strip():
                # Парсим строку файла: дата время атрибуты размер сжатый_размер имя
                parts = line.split()
                if len(parts) >= 6:
                    filename = ' '.join(parts[5:])
                    if filename and not filename.startswith('Date'):
                        # Определяем размер и тип
                        try:
                            size = int(parts[3]) if parts[3].isdigit() else 0
                        except (ValueError, IndexError):
                            size = 0
                        
                        is_dir = parts[2] == 'D' if len(parts) > 2 and len(parts[2]) == 1 else False
                        
                        entry = HBKEntry(
                            path=filename,
                            size=size,
                            is_dir=is_dir,
                            content=None  # Не извлекаем содержимое сразу
                        )
                        
                        entries.append(entry)
        
        # Сохраняем команду 7zip для дальнейшего использования
        self._zip_command = working_7z
        self._archive_path = file_path
        
        return entries
    
    def extract_file_content(self, filename: str) -> Optional[bytes]:
        """Извлекает содержимое конкретного файла по требованию."""
        if not self._zip_command or not self._archive_path:
            logger.error("Архив не был проинициализирован")
            return None
        
        try:
            return self._extract_single_file(self._archive_path, filename, self._zip_command)
        except Exception as e:
            logger.error(f"Ошибка извлечения файла {filename}: {e}")
            return None
    
    def _extract_single_file(self, archive_path: Path, filename: str, zip_cmd: str) -> Optional[bytes]:
        """Извлекает один файл из архива."""
        temp_dir = create_safe_temp_dir("hbk_extract_")
        
        try:
            # Безопасное извлечение файла
            result = safe_subprocess_run([
                zip_cmd, 'e', str(archive_path), filename, 
                f'-o{temp_dir}', '-y'
            ], timeout=30)
            
            if result.returncode == 0:
                # Ищем извлеченный файл
                extracted_files = list(temp_dir.rglob("*"))
                for extracted_file in extracted_files:
                    if extracted_file.is_file():
                        with open(extracted_file, 'rb') as f:
                            return f.read()
            
            return None
            
        except SafeSubprocessError as e:
            logger.error(f"Ошибка извлечения файла {filename}: {e}")
            return None
        finally:
            safe_remove_dir(temp_dir)
    
    def get_supported_files(self, directory: str) -> List[str]:
        """Возвращает список поддерживаемых файлов в директории."""
        supported_files = []
        
        if not os.path.exists(directory):
            return supported_files
        
        for file_name in os.listdir(directory):
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(file_name)[1].lower()
                if file_ext in self.supported_extensions:
                    supported_files.append(file_path)
        
        return supported_files
