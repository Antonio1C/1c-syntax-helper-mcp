#!/usr/bin/env python3
"""Тестирование HTML парсера на всех файлах из data/html."""

import sys
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.append(str(Path(__file__).parent))

from src.parsers.html_parser import HTMLParser

def test_html_parser():
    """Тестирует HTML парсер на всех файлах из data/html."""
    print("=== Тестирование HTML парсера ===")
    
    # Путь к каталогу с HTML файлами
    html_dir = Path("data/html")
    html_files = list(html_dir.glob("*.html"))
    
    print(f"📂 Найдено файлов: {len(html_files)}")
    
    # Создаем парсер
    parser = HTMLParser()
    
    for i, html_file_path in enumerate(html_files, 1):
        print(f"\n{'='*60}")
        print(f"📄 Файл {i}/{len(html_files)}: {html_file_path.name}")
        print('='*60)
        
        # Читаем содержимое файла
        with open(html_file_path, 'rb') as f:
            html_content = f.read()
        
        print(f"✅ Файл прочитан: {len(html_content)} байт")
        
        # Создаем путь для парсера (симулируем структуру 1С)
        file_path = f"objects/catalog125/catalog168/object170/events/{html_file_path.name}"
        doc = parser.parse_html_content(html_content, file_path)
        
        print("✅ HTML успешно распарсен!")
        print("\n--- Результат парсинга ---")
        print(f"ID: {doc.id}")
        print(f"Тип: {doc.type}")
        print(f"Имя: {doc.name}")
        print(f"Объект: {doc.object}")
        print(f"Описание: {doc.description}")
        print(f"Синтаксис: {doc.syntax_ru}")
        print(f"Возвращаемое значение: {doc.return_type}")
        if hasattr(doc, 'usage') and doc.usage:
            print(f"Использование: {doc.usage}")
        print(f"Версия: {doc.version_from}")
        print(f"Параметры: {len(doc.parameters)}")
        
        for j, param in enumerate(doc.parameters, 1):
            print(f"  {j}. {param.name} ({param.type}): {param.description}")
        
        print(f"\nПримеры: {len(doc.examples)}")
        for j, example in enumerate(doc.examples, 1):
            print(f"  {j}. {example}")
        
        # Информация для объектов
        if hasattr(doc, 'methods') and doc.methods:
            print(f"\nМетоды: {len(doc.methods)}")
            for j, method in enumerate(doc.methods, 1):
                print(f"  {j}. {method.name} ({method.name_en})")
        
        if hasattr(doc, 'properties') and doc.properties:
            print(f"\nСвойства: {len(doc.properties)}")
            for j, prop in enumerate(doc.properties, 1):
                print(f"  {j}. {prop.name} ({prop.name_en})")
        
        if hasattr(doc, 'events') and doc.events:
            print(f"\nСобытия: {len(doc.events)}")
            for j, event in enumerate(doc.events, 1):
                print(f"  {j}. {event.name} ({event.name_en})")
    
    print(f"\n{'='*60}")
    print(f"✅ Обработка завершена. Всего файлов: {len(html_files)}")
    print('='*60)

if __name__ == "__main__":
    test_html_parser()
