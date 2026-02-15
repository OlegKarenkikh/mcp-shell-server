# MCP Shell Server

MCP-сервер с shell-доступом для интеграции с [Perplexity AI](https://perplexity.ai).

Мульти-проектный workspace: клонируй любые репозитории, переключайся между ними, запускай тесты и редактируй файлы.

**Endpoint:** `https://mcp.olegk.su/sse`

## Tools

| Tool | Описание |
|------|----------|
| `clone(repo, branch?)` | Клонировать репо из GitHub (имя или URL) |
| `projects()` | Показать все проекты и активный |
| `switch(project)` | Переключить активный проект |
| `run(command, cwd?)` | Запустить shell-команду в активном проекте |
| `cat(path)` | Прочитать файл |
| `write(path, content)` | Записать файл |
| `ls(path?)` | Показать содержимое директории |

## Deploy via Coolify

### 1. Создать ресурс

1. Coolify → **New Resource** → **Public Repository**
2. URL: `https://github.com/OlegKarenkikh/mcp-shell-server`
3. Branch: `main`, Build Pack: **Docker Compose**
4. Docker Compose Location: `/docker-compose.yml`
5. **Load Compose File** → **Save**

### 2. Environment Variables

Сгенерировать пароль на сервере:
```bash
apt-get install -y apache2-utils
htpasswd -nbB oleg YourStrongPassword
```

Вывод будет например: `oleg:$2y$05$abc123...`

В Coolify → **Environment Variables** добавить:
```
WORKSPACE_PATH=/opt/mcp-workspace
GITHUB_USER=OlegKarenkikh
AUTH_CREDENTIALS=oleg:$$2y$$05$$abc123...
```

> **Важно:** каждый `$` в хеше нужно удвоить `$$` для docker-compose!

### 3. Deploy

Coolify автоматически:
- Назначит домен `mcp.olegk.su` через `SERVICE_FQDN_MCP_8008`
- Выпустит Let's Encrypt SSL
- Настроит Traefik proxy (443 → 8008)
- Включит Basic Auth

Endpoint: `https://mcp.olegk.su/sse`

### 4. Проверка

```bash
# Без авторизации — должен вернуть 401
curl https://mcp.olegk.su/sse

# С авторизацией — должен вернуть event: endpoint
curl -N -u oleg:YourStrongPassword https://mcp.olegk.su/sse
```

### 5. Подключить к Perplexity

Settings → Connectors → Remote MCP:
- URL: `https://mcp.olegk.su/sse`
- Auth: Basic Auth → `oleg` / `YourStrongPassword`

## Безопасность

- HTTPS + Let's Encrypt SSL (авто через Coolify)
- Basic Auth через Traefik middleware
- Все пути ограничены WORKSPACE
- Таймаут команд: 120с
- Ресурсы: 512MB RAM, 1 CPU
- Нет открытых портов (всё через Traefik proxy)

## Переменные окружения

| Переменная | Описание |
|---|---|
| `WORKSPACE_PATH` | Путь на хосте для проектов |
| `GITHUB_USER` | GitHub-пользователь для clone() |
| `AUTH_CREDENTIALS` | `user:$$hash` для Basic Auth |
| `CMD_TIMEOUT` | Таймаут команд (сек) |
| `MAX_OUTPUT` | Макс. длина вывода |
| `MAX_FILE_READ` | Макс. длина файла |
