FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    requests \
    beautifulsoup4

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

CMD ["/bin/bash"]
