@echo off
REM MCP Server Start Script for Windows
REM Скрипт запуска MCP сервера для Windows

echo Starting 1C Syntax Helper MCP Server...
echo Запуск MCP сервера синтаксис-помощника 1С...

REM Check if virtual environment exists
REM Проверяем существование виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Please run: python -m venv venv
    echo Пожалуйста выполните: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
REM Активируем виртуальное окружение
echo Activating virtual environment...
echo Активируем виртуальное окружение...
call venv\Scripts\activate.bat

REM Set PYTHONPATH
REM Устанавливаем PYTHONPATH
set PYTHONPATH=%CD%

echo Environment variables:
echo Переменные окружения:
echo   PYTHONPATH=%PYTHONPATH%
echo   Note: Other settings loaded from .env file
echo   Примечание: Остальные настройки загружаются из .env файла

REM Start the server
REM Запускаем сервер
echo Starting MCP server on http://localhost:8000
echo Запускаем MCP сервер на http://localhost:8000
echo Press Ctrl+C to stop the server
echo Нажмите Ctrl+C для остановки сервера
echo.
echo To force reindex, use: start_mcp_server.bat --reindex
echo Для принудительной переиндексации: start_mcp_server.bat --reindex
echo.

python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload %*

echo Server stopped.
echo Сервер остановлен.
pause