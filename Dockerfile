FROM python:3.11-slim

LABEL maintainer="Kiran Rajanna <kiranshadow@gmail.com>"
LABEL description="CMIPS AWS inventory tool - maps and inventories AWS resources across 150+ services"
LABEL version="1.8.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir .

# Create output and data directories
RUN mkdir -p /app/output /root/.cmipsmap

# Default entrypoint
ENTRYPOINT ["cmipsmap"]

# Default command (show help)
CMD ["--help"]
