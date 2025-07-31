FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app

# Install system dependencies and AWS CLI
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && ARCH=$(dpkg --print-architecture) \
    && if [ "$ARCH" = "amd64" ]; then AWS_CLI_ARCH="x86_64"; else AWS_CLI_ARCH="aarch64"; fi \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_CLI_ARCH}.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Copy entire project (respecting .dockerignore)
COPY . .

# Install dependencies




# Install from requirements file
RUN python -m pip install --no-cache-dir -r requirements.txt





# Set AWS region environment variable

ENV AWS_REGION=us-east-1
ENV AWS_DEFAULT_REGION=us-east-1


# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1


RUN python -m pip install aws_opentelemetry_distro_genai_beta>=0.1.2


# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080

# Use the full module path

CMD ["opentelemetry-instrument", "python", "-m", "agent"]
