# Multi-stage: Node (supergateway) + Python (MCP server)
FROM node:20-slim AS node-base
RUN npm install -g supergateway

FROM python:3.12-slim

# Copy Node.js + supergateway from node stage
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/supergateway/bin/supergateway.js /usr/local/bin/supergateway

# Install Python MCP SDK
RUN pip install --no-cache-dir "mcp[cli]"

# Copy server
WORKDIR /workspace
COPY shell_mcp_server.py /opt/mcp/

# Non-root user for security
RUN useradd -m mcp && chown -R mcp:mcp /opt/mcp /workspace

EXPOSE 8000

# supergateway wraps stdio MCP server into SSE HTTP
CMD ["node", "/usr/local/lib/node_modules/supergateway/bin/supergateway.js", \
     "--stdio", "python3 /opt/mcp/shell_mcp_server.py", \
     "--port", "8000"]
