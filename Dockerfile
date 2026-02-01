FROM python:3.11-slim

LABEL maintainer="Tarek CHEIKH <tarek@tocconsulting.fr>"
LABEL description="A fast, comprehensive tool for mapping and inventorying AWS resources across 140+ services"
LABEL version="1.1.0"

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

# Create output directory
RUN mkdir -p /app/output

# Default entrypoint
ENTRYPOINT ["awsmap"]

# Default command (show help)
CMD ["--help"]
