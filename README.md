# MCP Shell Server

MCP-сервер с shell-доступом для интеграции с [Perplexity AI](https://perplexity.ai).

Предоставляет инструменты `run`, `cat`, `write`, `ls` через MCP protocol.
Использует [supergateway](https://github.com/supercorp-ai/supergateway) для трансляции stdio → SSE (HTTP).

**Endpoint:** `https://mcp.olegk.su/sse`

## Tools

| Tool | Описание |
|------|----------|
| `run(command, cwd?)` | Запустить shell-команду, вернуть stdout+stderr |
| `cat(path)` | Прочитать файл |
| `write(path, content)` | Записать файл |
| `ls(path?)` | Показать содержимое директории |

## Deploy via Coolify

### 1. Создать ресурс

1. Coolify → **New Resource** → **Docker Compose**
2. Указать этот репозиторий или вставить `docker-compose.yml`
3. В **Environment Variables** задать:
   ```
   PROJECT_PATH=/home/oleg/Purchase
   ```

### 2. Настроить домен

Coolify автоматически настроит reverse proxy + Let's Encrypt SSL.

В настройках сервиса указать домен:
```
mcp.olegk.su
```

Endpoint после деплоя:
```
https://mcp.olegk.su/sse
```

### 3. Защита доступа

**Вариант A: Traefik Basic Auth** (через Coolify labels):
```yaml
labels:
  - "traefik.http.middlewares.mcp-auth.basicauth.users=user:$$apr1$$..."
  - "traefik.http.routers.mcp.middlewares=mcp-auth"
```

Сгенерировать пароль:
```bash
htpasswd -nb user password
```

**Вариант B: Cloudflare Tunnel** — Zero Trust без открытых портов.

### 4. Подключить к Perplexity

- **Mac app**: Settings → Connectors → Remote MCP → URL: `https://mcp.olegk.su/sse`
- **Web** (когда Remote MCP станет доступен): аналогично

## Локальный запуск

```bash
# Без Docker
pip install "mcp[cli]"
python3 shell_mcp_server.py

# С Docker
cp .env.example .env
# отредактировать .env
docker compose up -d
```

## Безопасность

- Все пути ограничены `PROJECT_DIR` (path traversal protection)
- Таймаут команд: `CMD_TIMEOUT` (по умолчанию 120с)
- Вывод обрезается до `MAX_OUTPUT` символов
- Контейнер работает от непривилегированного пользователя `mcp`
- Ресурсы ограничены: 512MB RAM, 1 CPU

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `PROJECT_DIR` | `/workspace` | Рабочая директория внутри контейнера |
| `CMD_TIMEOUT` | `120` | Таймаут выполнения команд (сек) |
| `MAX_OUTPUT` | `4000` | Макс. длина вывода команды |
| `MAX_FILE_READ` | `8000` | Макс. длина читаемого файла |
