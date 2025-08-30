
"""Парсер .hbk файлов (архивы документации 1С)."""

import os
import zipfile
import py7zr
import tempfile
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.models.doc_models import HBKFile, HBKEntry, ParsedHBK, CategoryInfo
from src.core.logging import get_logger
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
        """Извлекает содержимое архива."""
        entries = []
        
        # Сначала пробуем через внешний 7zip (наиболее надежный метод)
        try:
            entries = self._extract_external_7z(file_path)
            if entries:
                logger.info("Файл успешно обработан через внешний 7zip")
                return entries
        except Exception as e:
            logger.debug(f"Не удалось обработать через внешний 7zip: {e}")
        
        # Fallback: пробуем как 7Z архив через py7zr
        try:
            entries = self._extract_7z(file_path)
            if entries:
                logger.info("Файл успешно обработан как 7Z архив")
                return entries
        except Exception as e:
            logger.debug(f"Не удалось обработать как 7Z: {e}")
        
        # Fallback: пробуем как ZIP архив
        try:
            entries = self._extract_zip(file_path)
            if entries:
                logger.info("Файл успешно обработан как ZIP архив")
                return entries
        except Exception as e:
            logger.debug(f"Не удалось обработать как ZIP: {e}")
        
        logger.error(f"Не удалось определить формат архива: {file_path}")
        return []
    
    def _extract_zip(self, file_path: Path) -> List[HBKEntry]:
        """Извлекает содержимое ZIP архива."""
        entries = []
        
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            for info in zip_file.infolist():
                entry = HBKEntry(
                    path=info.filename,
                    size=info.file_size,
                    is_dir=info.is_dir()
                )
                
                # Читаем содержимое только для небольших файлов
                if not entry.is_dir and entry.size < self._max_file_size // 100:  # < 1% от максимального размера
                    try:
                        entry.content = zip_file.read(info.filename)
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать {info.filename}: {e}")
                
                entries.append(entry)
        
        return entries
    
    def _extract_7z(self, file_path: Path) -> List[HBKEntry]:
        """Извлекает содержимое 7Z архива."""
        entries = []
        
        with py7zr.SevenZipFile(file_path, mode='r') as sz_file:
            for info in sz_file.list():
                entry = HBKEntry(
                    path=info.filename,
                    size=info.uncompressed if hasattr(info, 'uncompressed') else 0,
                    is_dir=info.is_directory if hasattr(info, 'is_directory') else False
                )
                entries.append(entry)
            
            # Извлекаем содержимое файлов
            if entries:
                extracted = sz_file.readall()
                for entry in entries:
                    if not entry.is_dir and entry.path in extracted:
                        entry.content = extracted[entry.path].read()
        
        return entries
    
    def _analyze_structure(self, entries: List[HBKEntry], result: ParsedHBK):
        """Анализирует структуру архива и извлекает документацию."""
        
        # Статистика
        html_files = 0
        st_files = 0
        category_files = 0
        
        # Группируем файлы по каталогам
        directories = {}
        
        for entry in entries:
            if entry.is_dir:
                continue
                
            path_parts = entry.path.replace('\\', '/').split('/')
            
            # Анализируем файлы __categories__
            if path_parts[-1] == '__categories__':
                category_files += 1
                self._parse_categories_file(entry, result)
                continue
            
            # Анализируем .html файлы
            if entry.path.endswith('.html'):
                html_files += 1
                # Пока просто считаем, парсинг будет в HTMLParser
                continue
            
            # Анализируем .st файлы (шаблоны)
            if entry.path.endswith('.st'):
                st_files += 1
                # Пока просто считаем
                continue
        
        # Обновляем статистику
        result.stats = {
            'html_files': html_files,
            'st_files': st_files,
            'category_files': category_files,
            'total_entries': len(entries)
        }
        
        logger.info(f"Структура архива: HTML={html_files}, ST={st_files}, Categories={category_files}")
    
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
        """Извлекает список файлов из архива через внешний 7zip (без извлечения содержимого)."""
        entries = []
        
        # Ищем доступный 7zip
        zip_commands = ['7z', '7z.exe']
        working_7z = None
        
        for cmd in zip_commands:
            try:
                result = safe_subprocess_run([cmd], timeout=5)
                if result.returncode == 0 or 'Igor Pavlov' in result.stdout or '7-Zip' in result.stdout:
                    working_7z = cmd
                    break
            except SafeSubprocessError:
                continue
        
        if not working_7z:
            raise HBKParserError("7zip не найден в системе")
        
        # Получаем список файлов (без извлечения)
        try:
            result = safe_subprocess_run([working_7z, 'l', str(file_path)], timeout=60)
        except SafeSubprocessError as e:
            raise HBKParserError(f"Ошибка чтения архива: {e}")
        
        if result.returncode != 0:
            raise HBKParserError(f"Ошибка чтения архива: {result.stderr}")
        
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
