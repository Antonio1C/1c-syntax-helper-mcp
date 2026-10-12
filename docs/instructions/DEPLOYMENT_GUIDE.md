# Инструкция по развертыванию

Руководство по развертыванию MCP-сервера синтаксис-помощника 1С на Windows 10/11 и Linux Server (AMD64 или ARM64).

## 📋 Содержание

1. [Требования](#требования)
2. [Подготовка Docker образа](#подготовка-docker-образа)
3. [Развертывание на сервере](#развертывание-на-сервере)
4. [Проверка работоспособности](#проверка-работоспособности)
5. [Подключение клиентов](#подключение-клиентов)
6. [Обновление .hbk файла](#обновление-hbk-файла)
7. [Управление сервисом](#управление-сервисом)

---

## 🖥️ Требования

### Windows 10/11 (AMD64)
- Версия Windows, поддерживаемая Docker Desktop
- Docker Desktop с Linux containers и Docker Compose v2
- 8+ ГБ RAM рекомендуется для Docker Desktop и Elasticsearch

Docker Desktop официально не поддерживается на Windows Server. См. [системные требования Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/#system-requirements).

### Linux Server (AMD64 или ARM64)
- Linux для целевой архитектуры
- Docker Engine и Docker Compose v2
- 4+ ГБ RAM (рекомендуется 8 ГБ)

### Проверка Docker:
```powershell
# Windows
docker --version
docker compose version
```

```bash
# Linux
docker --version
docker compose version
```

---

## 📦 Подготовка Docker образа

### На вашей рабочей машине:

#### Для серверов AMD64 (Intel/AMD)

```powershell
# Перейти в корень клона проекта
Set-Location "C:\path\to\help1c"

# 2. Собрать Docker образ для AMD64
docker build -t help1c-mcp:amd64 .

# 3. Экспортировать образ в файл
docker save help1c-mcp:amd64 -o help1c-mcp-amd64.tar

# Образ сохранится в файл help1c-mcp-amd64.tar (~500 МБ)
```

#### Для серверов ARM64 (ARM, Raspberry Pi 4+, Apple Silicon)

```powershell
# Перейти в корень клона проекта
Set-Location "C:\path\to\help1c"

# 2. Собрать Docker образ для ARM64 (требует Docker Buildx)
docker buildx build --platform linux/arm64 -t help1c-mcp:arm64 -o type=docker .

# 3. Экспортировать образ в файл
docker save help1c-mcp:arm64 -o help1c-mcp-arm64.tar

# Образ сохранится в файл help1c-mcp-arm64.tar (~500 МБ)

# Примечание: Если Docker Buildx не установлен, используйте:
# docker buildx create --name multiarch
# docker buildx use multiarch
```

---

## 🚀 Развертывание на сервере

### Развертывание на Windows 10/11 (AMD64)

#### Шаг 1: Подготовка каталога развертывания

На компьютере Windows 10/11 с запущенным Docker Desktop создайте каталог `C:\help1c-mcp\` и скопируйте туда образ, Compose-файл и HBK. Если образ собирался на другом компьютере, сначала перенесите эти файлы на Windows-хост.

```
C:\help1c-mcp\
├── help1c-mcp-amd64.tar     # Docker образ для AMD64
├── docker-compose.yml       # Конфигурация
└── data\
  ├── hbk\
  │   └── shcntx_ru.hbk        # Файл документации 1С
  └── logs\                    # Каталог создаётся Compose при запуске
```

```powershell
# Выполнять из корня клона проекта на Windows-хосте
New-Item -Path "C:\help1c-mcp\data\hbk" -ItemType Directory -Force
New-Item -Path "C:\help1c-mcp\data\logs" -ItemType Directory -Force

# Скопировать файлы
Copy-Item ".\help1c-mcp-amd64.tar" "C:\help1c-mcp\"
Copy-Item ".\docker-compose.yml" "C:\help1c-mcp\"
Copy-Item ".\data\hbk\shcntx_ru.hbk" "C:\help1c-mcp\data\hbk\"
```

#### Шаг 2: Загрузка образа

Убедитесь, что Docker Desktop запущен в режиме Linux containers, затем выполните в PowerShell:

```powershell
Set-Location C:\help1c-mcp

# Загрузить Docker образ
docker load -i help1c-mcp-amd64.tar

# Проверить, что образ загружен
docker images | Select-String "help1c-mcp"
```

#### Шаг 3: Настройка Compose

Замените в `C:\help1c-mcp\docker-compose.yml` строку `build: .` на `image: help1c-mcp:amd64`:

```yaml
mcp-server:
  image: help1c-mcp:amd64     # ← Изменить эту строку
  container_name: mcp-1c-helper
  ports:
    - "8000:8000"
  # ... остальное без изменений
```

#### Шаг 4: Запуск сервиса

```powershell
Set-Location C:\help1c-mcp

# Запустить контейнеры
docker compose up -d

# Проверить статус
docker compose ps
```

---

### Развертывание на Linux Server (AMD64 или ARM64)

#### Шаг 1: Определить архитектуру сервера

На Linux-сервере выполните:

```bash
uname -m
```

`x86_64` означает AMD64, `aarch64` означает ARM64. Используйте образ, собранный для соответствующей архитектуры в разделе подготовки образа.

#### Шаг 2: Копирование файлов на Linux-сервер

На Windows-компьютере в PowerShell из корня клона проекта выберите соответствующий архив и скопируйте пакет:

```powershell
$ImageTar = "help1c-mcp-amd64.tar" # Для ARM64 замените на help1c-mcp-arm64.tar
ssh user@server "mkdir -p /opt/help1c-mcp/data/hbk /opt/help1c-mcp/data/logs"
scp ".\$ImageTar" user@server:/opt/help1c-mcp/
scp .\docker-compose.yml user@server:/opt/help1c-mcp/
scp .\data\hbk\shcntx_ru.hbk user@server:/opt/help1c-mcp/data/hbk/
```

#### Шаг 3: Загрузка образа на Linux-сервере

Выберите команду, соответствующую архитектуре:

```bash
cd /opt/help1c-mcp
docker load -i help1c-mcp-amd64.tar  # AMD64
# Для ARM64: docker load -i help1c-mcp-arm64.tar
docker images | grep help1c-mcp
```

#### Шаг 4: Настройка Compose

Отредактируйте `/opt/help1c-mcp/docker-compose.yml`: замените `build: .` в сервисе `mcp-server` на соответствующий локальный образ:

```yaml
mcp-server:
  image: help1c-mcp:amd64 # Для ARM64 используйте help1c-mcp:arm64
  container_name: mcp-1c-helper
  ports:
    - "8000:8000"
  # Остальные параметры и volumes оставьте как в docker-compose.yml проекта.
```

#### Шаг 5: Запуск контейнеров

```bash
cd /opt/help1c-mcp
docker compose up -d
docker compose ps
```

**Ожидаемый результат:**
```
NAME              STATUS              PORTS
es-1c-helper      Up 2 minutes        0.0.0.0:9200->9200/tcp
mcp-1c-helper     Up 1 minute         0.0.0.0:8000->8000/tcp
```

---

## ✅ Проверка работоспособности

### На сервере:

```powershell
# Проверка health endpoint
Invoke-RestMethod http://localhost:8000/health

# Проверка статуса индекса
Invoke-RestMethod http://localhost:8000/index/status
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "elasticsearch": true,
  "index_exists": true,
  "documents_count": 1234
}
```

### С клиентской машины:

Замените `SERVER_IP` на IP адрес сервера (например, `192.168.1.100`):

```powershell
Invoke-RestMethod http://SERVER_IP:8000/health
```

---

## 💻 Подключение клиентов

### Настройка VS Code на клиентских машинах

Создайте файл `.vscode/mcp.json` в папке проекта клиента (или добавьте сервер через MCP user configuration):

```json
{
  "servers": {
    "mcp-helper1c-http": {
      "url": "http://SERVER_IP:8000/mcp",
      "type": "http"
    }
  },
  "inputs": []
}
```

**Замените `SERVER_IP`** на реальный IP адрес сервера:
- Пример: `http://192.168.1.100:8000/mcp`
- Или DNS имя: `http://help1c-server.local:8000/mcp`

### Проверка подключения в VS Code

1. Откройте VS Code
2. Нажмите `Ctrl+Shift+P`
3. Выполните `MCP: List Servers` и запустите `mcp-helper1c-http`
4. В чате с AI попросите: "Найди справку по СтрДлина"

---

## 🔄 Обновление .hbk файла

### На Windows 10/11

```powershell
# 1. Заменить файл на сервере
Copy-Item "путь\к\новому\файлу.hbk" "C:\help1c-mcp\data\hbk\shcntx_ru.hbk" -Force

# 2. Запустить реиндексацию через API
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/index/rebuild"

# 3. Проверить результат
Invoke-RestMethod -Uri "http://localhost:8000/index/status"
```

**Время обновления:** ~1-5 минут  
**Преимущества:** Контейнеры не перезагружаются, пользователи не отключаются

### На Linux Server

```bash
# 1. Заменить файл на сервере
cd /opt/help1c-mcp
cp /путь/к/новому/файлу.hbk data/hbk/shcntx_ru.hbk

# 2. Запустить реиндексацию через API
curl -X POST http://localhost:8000/index/rebuild

# 3. Проверить результат
curl http://localhost:8000/index/status
```

**Время обновления:** ~1-5 минут  
**Преимущества:** Контейнеры не перезагружаются, пользователи не отключаются

### Если нужно перезагрузить контейнер

На Windows 10/11:
```powershell
Set-Location C:\help1c-mcp
docker compose restart mcp-server
```

На Linux Server:
```bash
cd /opt/help1c-mcp
docker compose restart
```

**Простой:** ~30 секунд

### Автоматизация

Создайте файл `C:\help1c-mcp\update-hbk.ps1`:

```powershell
$HbkSource = "\\server\share\shcntx_ru.hbk"
$HbkDest = "C:\help1c-mcp\data\hbk\shcntx_ru.hbk"

Write-Host "Копирование файла..."
Copy-Item $HbkSource $HbkDest -Force

Write-Host "Реиндексация..."
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/index/rebuild"

Write-Host "Готово!"
Invoke-RestMethod -Uri "http://localhost:8000/index/status"
```

Запускать: `.\update-hbk.ps1`

## Управление сервисом

```powershell
# Просмотр логов только MCP сервера
docker compose logs -f mcp-server

# Просмотр статуса
docker compose ps

# После загрузки нового tar-образа обновить контейнер MCP
docker compose up -d --force-recreate mcp-server

# Полная очистка (с удалением данных)
docker compose down -v
```

### Автоматический запуск при загрузке сервера

**Linux (systemd):**

Создайте файл `/etc/systemd/system/help1c-mcp.service`:

```ini
[Unit]
Description=1C Syntax Helper MCP Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/help1c-mcp
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активируйте сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable help1c-mcp
sudo systemctl start help1c-mcp
sudo systemctl status help1c-mcp
```

**Windows 10/11:**

В `docker-compose.yml` уже установлен `restart: unless-stopped`, поэтому контейнеры автоматически запустятся при загрузке сервера (если Docker Desktop настроен на автозапуск).

---

## 🛠️ Устранение проблем

### Контейнеры не запускаются

**Windows 10/11:**
```powershell
# Посмотреть логи
docker compose logs

# Порты заняты? Проверить:
netstat -ano | findstr ":8000"
netstat -ano | findstr ":9200"

# Полная переустановка
docker compose down -v
docker compose up -d
```

**Linux Server:**
```bash
# Посмотреть логи
docker compose logs

# Порты заняты? Проверить:
netstat -tulpn | grep -E ":8000|:9200"

# Полная переустановка
docker compose down -v
docker compose up -d
```

### Нет доступа с клиентских машин

**Windows 10/11:**
```powershell
# Открыть порт в firewall
New-NetFirewallRule -DisplayName "Help1C MCP" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Проверить доступность
Test-NetConnection -ComputerName SERVER_IP -Port 8000
```

**Linux Server:**
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw reload

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### Индексация не работает

**Windows 10/11:**
```powershell
# Проверить наличие файла
dir C:\help1c-mcp\data\hbk\

# Посмотреть логи контейнера
docker compose logs mcp-server

# Перезапустить реиндексацию
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/index/rebuild"
```

**Linux Server:**
```bash
# Проверить наличие файла
ls -lh /opt/help1c-mcp/data/hbk/

# Посмотреть логи контейнера
docker compose logs mcp-server

# Перезапустить реиндексацию
curl -X POST http://localhost:8000/index/rebuild
```

### Проверить статус здоровья сервиса

**Windows 10/11:**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

**Linux Server:**
```bash
curl http://localhost:8000/health
```

---

## ✅ Чек-лист развертывания

### Windows 10/11
- [ ] Docker Desktop установлен и запущен
- [ ] Образ `help1c-mcp:amd64` собран
- [ ] Файл `help1c-mcp-amd64.tar` создан
- [ ] Файлы скопированы в `C:\help1c-mcp\`
- [ ] HBK-файл на месте: `C:\help1c-mcp\data\hbk\shcntx_ru.hbk`
- [ ] `docker-compose.yml` обновлен (image: help1c-mcp:amd64)
- [ ] Контейнеры запущены: `docker compose ps`
- [ ] Health check работает: `Invoke-RestMethod http://localhost:8000/health`
- [ ] Порт 8000 открыт в firewall
- [ ] Клиенты могут подключиться: `Invoke-RestMethod http://SERVER_IP:8000/health`

### Linux Server (AMD64 или ARM64)
- [ ] Собран образ для архитектуры сервера (`help1c-mcp:amd64` или `help1c-mcp:arm64`)
- [ ] Создан соответствующий tar-файл (`help1c-mcp-amd64.tar` или `help1c-mcp-arm64.tar`)
- [ ] Файлы скопированы в `/opt/help1c-mcp/`
- [ ] HBK-файл на месте: `/opt/help1c-mcp/data/hbk/shcntx_ru.hbk`
- [ ] `docker-compose.yml` обновлен с image tag нужной архитектуры
- [ ] Образ загружен: `docker images | grep help1c-mcp`
- [ ] Контейнеры запущены: `docker compose ps`
- [ ] Health check работает: `curl http://localhost:8000/health`
- [ ] Порт 8000 открыт в firewall (`ufw allow 8000/tcp`)
- [ ] Клиенты могут подключиться: `curl http://SERVER_IP:8000/health`

---

**Дата:** 29.12.2025  
**Версия:** 3