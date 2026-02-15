# Multi-stage: Node (supergateway) + Python (MCP server)
FROM node:20-slim AS node-base
RUN npm install -g supergateway

FROM python:3.12-slim

# Copy Node.js + supergateway from node stage
COPY --from=node-base /usr/local/bin/node /usr/local/bin/node
COPY --from=node-base /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/supergateway/bin/supergateway.js /usr/local/bin/supergateway

# Install Python MCP SDK + git (for clone tool)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir "mcp[cli]"

# Copy server
WORKDIR /workspace
COPY shell_mcp_server.py /opt/mcp/

EXPOSE 8008

CMD ["node", "/usr/local/lib/node_modules/supergateway/bin/supergateway.js", \
     "--stdio", "python3 /opt/mcp/shell_mcp_server.py", \
     "--port", "8008"]
