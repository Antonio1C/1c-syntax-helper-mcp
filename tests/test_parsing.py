"""Тест 2: Парсинг .hbk файла."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import settings
from src.parsers.hbk_parser import HBKParser


async def test_hbk_parsing():
    """Тест парсинга .hbk файла."""
    print("=== Тест 2: Парсинг .hbk файла ===")
    
    try:
        # Ищем .hbk файл
        hbk_dir = Path(settings.data.hbk_directory)
        hbk_files = list(hbk_dir.glob("*.hbk"))
        
        if not hbk_files:
            print(f"❌ .hbk файлы не найдены в {hbk_dir}")
            return False
        
        hbk_file = hbk_files[0]
        print(f"📁 Найден файл: {hbk_file}")
        print(f"📊 Размер: {hbk_file.stat().st_size / 1024 / 1024:.1f} МБ")
        
        # Парсим файл
        parser = HBKParser()
        parsed_hbk = parser.parse_file(str(hbk_file))
        
        if not parsed_hbk:
            print("❌ Ошибка парсинга файла")
            return False
        
        print(f"✅ Парсинг завершен успешно:")
        print(f"   • Записей в архиве: {parsed_hbk.file_info.entries_count}")
        print(f"   • Найдено документов: {len(parsed_hbk.documentation)}")
        print(f"   • Категорий: {len(parsed_hbk.categories)}")
        print(f"   • Ошибок: {len(parsed_hbk.errors)}")
        
        # Показываем первые несколько документов
        if parsed_hbk.documentation:
            print("\nПример найденных документов:")
            for i, doc in enumerate(parsed_hbk.documentation[:3], 1):
                print(f"   {i}. {doc.name} ({doc.type.value})")
        
        if parsed_hbk.errors:
            print(f"\nОшибки парсинга:")
            for error in parsed_hbk.errors[:3]:
                print(f"   • {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования парсера: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_hbk_parsing())
