"""
Точка входа для разработки (будет заменена на src/main.py)
"""

import sys
import os

# Добавляем src в Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from src.main import app
    
    print("🚀 Запуск MCP сервера синтаксис-помощника 1С")
    print("📡 Сервер будет доступен по адресу: http://localhost:8000")
    print("📚 Документация API: http://localhost:8000/docs")
    print("❤️  Health check: http://localhost:8000/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
