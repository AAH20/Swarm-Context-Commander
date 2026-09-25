FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir '.[mcp]'
USER 65534:65534
ENTRYPOINT ["swarm-context-mcp"]
