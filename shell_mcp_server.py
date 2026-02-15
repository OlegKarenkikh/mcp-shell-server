#!/usr/bin/env python3
"""MCP Shell Server for Perplexity AI integration.

Multi-project workspace with built-in Bearer token auth.
Runs as native SSE server via FastMCP.
"""

import os
import subprocess
import logging

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("mcp-shell")

WORKSPACE = os.environ.get("WORKSPACE", "/workspace")
TIMEOUT = int(os.environ.get("CMD_TIMEOUT", "120"))
MAX_OUTPUT = int(os.environ.get("MAX_OUTPUT", "4000"))
MAX_FILE_READ = int(os.environ.get("MAX_FILE_READ", "8000"))
GITHUB_USER = os.environ.get("GITHUB_USER", "OlegKarenkikh")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "")

STATE_FILE = os.path.join(WORKSPACE, ".mcp_active_project")

mcp = FastMCP("shell-runner", host="0.0.0.0", port=8008)


# ── Auth middleware ──

class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication middleware."""
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check
        if request.url.path == "/healthz":
            return await call_next(request)
        # Skip auth if no token configured
        if not AUTH_TOKEN:
            return await call_next(request)
        # Check Bearer token
        auth = request.headers.get("authorization", "")
        if auth == f"Bearer {AUTH_TOKEN}":
            return await call_next(request)
        return JSONResponse({"error": "Unauthorized"}, status_code=401)


# ── Helper functions ──

def _get_active_project() -> str:
    if os.path.exists(STATE_FILE):
        name = open(STATE_FILE).read().strip()
        path = os.path.join(WORKSPACE, name)
        if os.path.isdir(path):
            return path
    for entry in sorted(os.listdir(WORKSPACE)):
        full = os.path.join(WORKSPACE, entry)
        if os.path.isdir(full) and not entry.startswith("."):
            return full
    return WORKSPACE


def _set_active_project(name: str) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(name)


def _safe_path(path: str, base: str | None = None) -> str | None:
    if base is None:
        base = _get_active_project()
    full = os.path.join(base, path) if not os.path.isabs(path) else path
    real = os.path.realpath(full)
    if not real.startswith(os.path.realpath(WORKSPACE)):
        return None
    return real


# ── Tools ──

@mcp.tool()
def clone(repo: str, branch: str = "") -> str:
    """Clone a GitHub repository into the workspace.

    Args:
        repo: Repository name (e.g. 'Purchase') or full URL.
              If just a name, clones from GITHUB_USER account.
        branch: Branch to checkout (optional)
    """
    if repo.startswith("http") or repo.startswith("git@"):
        url = repo
        name = repo.rstrip("/").split("/")[-1].replace(".git", "")
    else:
        name = repo
        url = f"https://github.com/{GITHUB_USER}/{repo}.git"

    target = os.path.join(WORKSPACE, name)

    if os.path.isdir(target):
        cmd = f"git -C {target} pull"
        if branch:
            cmd = f"git -C {target} checkout {branch} && git -C {target} pull"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
        _set_active_project(name)
        output = (result.stdout + result.stderr).strip()
        return f"Updated existing repo. Active project: {name}\n{output}"

    cmd = f"git clone {url} {target}"
    if branch:
        cmd = f"git clone -b {branch} {url} {target}"

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip()}"
        _set_active_project(name)
        return f"Cloned {url} -> {name}. Active project: {name}\n{result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return f"ERROR: clone timed out after {TIMEOUT}s"


@mcp.tool()
def projects() -> str:
    """List all projects in the workspace and show active one."""
    active = os.path.basename(_get_active_project())
    entries = []
    for entry in sorted(os.listdir(WORKSPACE)):
        full = os.path.join(WORKSPACE, entry)
        if os.path.isdir(full) and not entry.startswith("."):
            marker = " <- active" if entry == active else ""
            is_git = os.path.isdir(os.path.join(full, ".git"))
            git_info = ""
            if is_git:
                try:
                    br = subprocess.run(
                        "git branch --show-current",
                        shell=True, cwd=full, capture_output=True, text=True, timeout=5
                    ).stdout.strip()
                    git_info = f"  [{br}]"
                except Exception:
                    git_info = "  [git]"
            entries.append(f"  {entry}{git_info}{marker}")
    if not entries:
        return "No projects in workspace. Use clone() to add one."
    return "Projects:\n" + "\n".join(entries)


@mcp.tool()
def switch(project: str) -> str:
    """Switch active project.

    Args:
        project: Project directory name in workspace
    """
    target = os.path.join(WORKSPACE, project)
    if not os.path.isdir(target):
        available = [e for e in os.listdir(WORKSPACE)
                     if os.path.isdir(os.path.join(WORKSPACE, e)) and not e.startswith(".")]
        return f"ERROR: '{project}' not found. Available: {', '.join(available)}"
    _set_active_project(project)
    return f"Active project: {project}"


@mcp.tool()
def run(command: str, cwd: str = "") -> str:
    """Run a shell command in the active project.

    Args:
        command: Shell command to execute
        cwd: Working directory relative to active project (optional)
    """
    base = _get_active_project()
    work_dir = base
    if cwd:
        resolved = _safe_path(cwd, base)
        if resolved is None:
            return "ERROR: working directory outside workspace"
        work_dir = resolved

    try:
        result = subprocess.run(
            command, shell=True, cwd=work_dir,
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            return f"OK (exit code {result.returncode}, no output)"
        if len(output) > MAX_OUTPUT:
            return f"... (truncated)\n{output[-MAX_OUTPUT:]}"
        return output
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {TIMEOUT}s"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def cat(path: str) -> str:
    """Read file content from the active project.

    Args:
        path: File path relative to active project root
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside workspace"
    if not os.path.isfile(resolved):
        return f"ERROR: not a file: {path}"
    try:
        content = open(resolved).read()
        if len(content) > MAX_FILE_READ:
            return f"... (showing last {MAX_FILE_READ} chars)\n{content[-MAX_FILE_READ:]}"
        return content
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def write(path: str, content: str) -> str:
    """Write content to a file in the active project.

    Args:
        path: File path relative to active project root
        content: File content to write
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside workspace"
    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w") as f:
            f.write(content)
        return f"OK: {len(content)} bytes -> {path}"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def ls(path: str = ".") -> str:
    """List directory contents in the active project.

    Args:
        path: Directory path relative to active project root
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside workspace"
    if not os.path.isdir(resolved):
        return f"ERROR: not a directory: {path}"
    try:
        entries = sorted(os.listdir(resolved))
        result = []
        for entry in entries:
            full = os.path.join(resolved, entry)
            prefix = "d" if os.path.isdir(full) else "f"
            size = os.path.getsize(full) if os.path.isfile(full) else ""
            result.append(f"[{prefix}] {entry}  {size}")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"ERROR: {e}"


# ── App with middleware ──

def create_app():
    """Create Starlette app with auth middleware wrapping MCP SSE."""
    from mcp.server.sse import SseServerTransport
    import uvicorn

    sse = SseServerTransport("/message")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0], streams[1], mcp._mcp_server.create_initialization_options()
            )

    async def handle_healthz(request: Request):
        return PlainTextResponse("ok")

    from starlette.routing import Route
    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/message", endpoint=sse.handle_post_message, methods=["POST"]),
            Route("/healthz", endpoint=handle_healthz),
        ],
        middleware=[Middleware(TokenAuthMiddleware)],
    )
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8008)
