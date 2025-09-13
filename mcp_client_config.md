# MCP Server Configuration for VS Code
# Конфигурация MCP сервера для VS Code

# Добавьте эту конфигурацию в ваш файл settings.json VS Code:
{
  "mcp.servers": {
    "1c-syntax-helper": {
      "command": "python",
      "args": [
        "-m", 
        "uvicorn", 
        "src.main:app", 
        "--host", 
        "127.0.0.1", 
        "--port", 
        "8000"
      ],
      "cwd": "d:\\Projects\\python\\help1c",
      "env": {
        "PYTHONPATH": "d:\\Projects\\python\\help1c",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}

# Альтернативная конфигурация для Claude Desktop:
# Добавьте в файл claude_desktop_config.json:
{
  "mcpServers": {
    "1c-syntax-helper": {
      "command": "python",
      "args": [
        "-m", 
        "uvicorn", 
        "src.main:app", 
        "--host", 
        "127.0.0.1", 
        "--port", 
        "8000"
      ],
      "cwd": "d:\\Projects\\python\\help1c",
      "env": {
        "PYTHONPATH": "d:\\Projects\\python\\help1c",
        "ELASTICSEARCH_HOST": "localhost",
        "ELASTICSEARCH_PORT": "9200",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}

# Для GitHub Copilot или других MCP клиентов:
# Используйте HTTP endpoint: http://localhost:8000/mcp