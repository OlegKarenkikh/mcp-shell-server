FROM python:3.12-slim

# Install git + curl (for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python MCP SDK + starlette + uvicorn
RUN pip install --no-cache-dir "mcp[cli]" starlette uvicorn

WORKDIR /workspace
COPY shell_mcp_server.py /opt/mcp/

EXPOSE 8008

CMD ["python3", "/opt/mcp/shell_mcp_server.py"]
