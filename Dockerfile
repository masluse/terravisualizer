# Multi-stage build for terravisualizer
# Stage 1: Build the binary
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev \
    binutils \
    zlib-dev

# Set working directory
WORKDIR /build

# Copy application files
COPY requirements.txt .
COPY setup.py .
COPY terravisualizer/ terravisualizer/
COPY terravisualizer.hcl .
COPY icons/ icons/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt pyinstaller==6.17.0

# Build the standalone executable
RUN pyinstaller --onefile \
    --add-data "terravisualizer.hcl:." \
    --add-data "icons:icons" \
    --name terravisualizer \
    terravisualizer/cli.py

# Stage 2: Runtime image
FROM alpine:latest

# Install runtime dependencies (Graphviz)
RUN apk add --no-cache graphviz ttf-dejavu

# Create a non-root user
RUN addgroup -S terravisualizer && adduser -S terravisualizer -G terravisualizer

# Copy the binary from builder stage
COPY --from=builder /build/dist/terravisualizer /usr/local/bin/terravisualizer
RUN chmod +x /usr/local/bin/terravisualizer

# Switch to non-root user
USER terravisualizer

# Set working directory
WORKDIR /data

# Set the entrypoint to terravisualizer
ENTRYPOINT ["terravisualizer"]

# Default command shows help if no arguments are provided
CMD ["--help"]
