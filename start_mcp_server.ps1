#!/bin/bash
# MCP Server Start Script for PowerShell/Unix
# Скрипт запуска MCP сервера для PowerShell/Unix

Write-Host "Starting 1C Syntax Helper MCP Server..." -ForegroundColor Green
Write-Host "Запуск MCP сервера синтаксис-помощника 1С..." -ForegroundColor Green

# Check if virtual environment exists
# Проверяем существование виртуального окружения
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "ОШИБКА: Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
    Write-Host "Пожалуйста выполните: python -m venv venv" -ForegroundColor Yellow
    Read-Host "Press Enter to exit / Нажмите Enter для выхода"
    exit 1
}

# Activate virtual environment
# Активируем виртуальное окружение
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
Write-Host "Активируем виртуальное окружение..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Set PYTHONPATH
# Устанавливаем PYTHONPATH
$env:PYTHONPATH = (Get-Location).Path

Write-Host "Environment variables:" -ForegroundColor Cyan
Write-Host "Переменные окружения:" -ForegroundColor Cyan
Write-Host "  PYTHONPATH=$env:PYTHONPATH" -ForegroundColor Gray
Write-Host "  Note: Other settings loaded from .env file" -ForegroundColor Green
Write-Host "  Примечание: Остальные настройки загружаются из .env файла" -ForegroundColor Green

# Start the server
# Запускаем сервер
Write-Host "Starting MCP server on http://localhost:8000" -ForegroundColor Green
Write-Host "Запускаем MCP сервер на http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "Нажмите Ctrl+C для остановки сервера" -ForegroundColor Yellow
Write-Host ""
Write-Host "To force reindex, use: .\start_mcp_server.ps1 --reindex" -ForegroundColor Cyan
Write-Host "Для принудительной переиндексации: .\start_mcp_server.ps1 --reindex" -ForegroundColor Cyan
Write-Host ""

# Передаём все аргументы скрипта в main.py
& ".\venv\Scripts\python.exe" src/main.py @args

Write-Host "Server stopped." -ForegroundColor Red
Write-Host "Сервер остановлен." -ForegroundColor Red