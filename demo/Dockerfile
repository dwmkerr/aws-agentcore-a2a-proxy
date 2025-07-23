FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY src/ ./src/

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "aws_bedrock_agentcore"]