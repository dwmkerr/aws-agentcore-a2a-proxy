FROM python:3.11-slim

WORKDIR /app

# Copy Python project files
COPY aws-bedrock-a2a-proxy/pyproject.toml aws-bedrock-a2a-proxy/uv.lock ./
RUN pip install uv && uv sync --frozen

# Copy source code
COPY aws-bedrock-a2a-proxy/src/ ./src/

EXPOSE 2972

CMD ["uv", "run", "python", "-m", "aws_bedrock_a2a_proxy"]