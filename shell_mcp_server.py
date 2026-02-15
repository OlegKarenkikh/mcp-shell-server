#!/usr/bin/env python3
"""MCP Shell Server for Perplexity AI integration.

Provides shell access, file read/write tools via MCP protocol.
Designed to run behind supergateway (stdio → SSE transport).

Security:
- All paths restricted to PROJECT_DIR
- Command timeout: 120s
- Output truncated to 4000 chars
- Path traversal protection
"""

import os
import subprocess

from mcp.server.fastmcp import FastMCP

PROJECT = os.environ.get("PROJECT_DIR", "/workspace")
TIMEOUT = int(os.environ.get("CMD_TIMEOUT", "120"))
MAX_OUTPUT = int(os.environ.get("MAX_OUTPUT", "4000"))
MAX_FILE_READ = int(os.environ.get("MAX_FILE_READ", "8000"))

mcp = FastMCP("shell-runner")


def _safe_path(path: str) -> str | None:
    """Resolve and validate path is within PROJECT."""
    full = os.path.join(PROJECT, path) if not os.path.isabs(path) else path
    real = os.path.realpath(full)
    if not real.startswith(os.path.realpath(PROJECT)):
        return None
    return real


@mcp.tool()
def run(command: str, cwd: str = "") -> str:
    """Run a shell command and return stdout+stderr.

    Args:
        command: Shell command to execute
        cwd: Working directory relative to project root (optional)
    """
    work_dir = PROJECT
    if cwd:
        resolved = _safe_path(cwd)
        if resolved is None:
            return "ERROR: working directory outside project root"
        work_dir = resolved

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
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
    """Read file content.

    Args:
        path: File path relative to project root
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside project root"
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
    """Write content to a file.

    Args:
        path: File path relative to project root
        content: File content to write
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside project root"
    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w") as f:
            f.write(content)
        return f"OK: {len(content)} bytes → {path}"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def ls(path: str = ".") -> str:
    """List directory contents.

    Args:
        path: Directory path relative to project root
    """
    resolved = _safe_path(path)
    if resolved is None:
        return "ERROR: path outside project root"
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
