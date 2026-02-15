# MCP Shell Server

MCP-сервер с shell-доступом для интеграции с [Perplexity AI](https://perplexity.ai).

Мульти-проектный workspace: клонируй любые репозитории, переключайся между ними, запускай тесты и редактируй файлы.
Использует [supergateway](https://github.com/supercorp-ai/supergateway) для трансляции stdio → SSE (HTTP).

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

## Рабочий процесс

```
# Клонировать проект (короткая форма — берёт из GITHUB_USER)
clone("Purchase")
clone("chatvlmllm", branch="develop")

# Посмотреть все проекты
projects()
#   Purchase  [main] ← active
#   chatvlmllm  [develop]

# Переключиться
switch("chatvlmllm")

# Запустить тесты
run("pytest tests/ -v --tb=short")

# Редактировать / читать
cat("src/main.py")
write("src/main.py", "...")
```

## Deploy via Coolify

### 1. Создать ресурс

1. Coolify → **New Resource** → **Docker Compose**
2. Указать этот репозиторий или вставить `docker-compose.yml`
3. В **Environment Variables** задать:
   ```
   WORKSPACE_PATH=/home/oleg/workspace
   GITHUB_USER=OlegKarenkikh
   ```

### 2. Настроить домен

В настройках сервиса указать домен:
```
mcp.olegk.su
```

Coolify автоматически настроит HTTPS + SSL.

Endpoint: `https://mcp.olegk.su/sse`

### 3. Подключить к Perplexity

Settings → Connectors → Remote MCP → `https://mcp.olegk.su/sse`

## Подготовка хоста

Перед первым деплоем создай директорию на сервере:

```bash
mkdir -p /home/oleg/workspace
```

Проекты будут клонироваться сюда через tool `clone()`.

## Безопасность

- Все пути ограничены `WORKSPACE` (path traversal protection)
- Таймаут команд: `CMD_TIMEOUT` (по умолчанию 120с)
- Вывод обрезается до `MAX_OUTPUT` символов
- Ресурсы: 512MB RAM, 1 CPU
- Рекомендуется закрыть доступ через Basic Auth или Cloudflare Tunnel

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `WORKSPACE_PATH` | `/home/oleg/workspace` | Путь на хосте для монтирования |
| `GITHUB_USER` | `OlegKarenkikh` | GitHub-пользователь для короткой формы clone() |
| `CMD_TIMEOUT` | `120` | Таймаут команд (сек) |
| `MAX_OUTPUT` | `4000` | Макс. длина вывода |
| `MAX_FILE_READ` | `8000` | Макс. длина файла |
