FROM node:20-slim

# Install Python + git
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv git && \
    rm -rf /var/lib/apt/lists/*

# Install supergateway globally
RUN npm install -g supergateway

# Install Python MCP SDK
RUN pip install --no-cache-dir --break-system-packages "mcp[cli]"

# Copy server
WORKDIR /workspace
COPY shell_mcp_server.py /opt/mcp/

EXPOSE 8008

CMD ["supergateway", \
     "--stdio", "python3 /opt/mcp/shell_mcp_server.py", \
     "--port", "8008"]
