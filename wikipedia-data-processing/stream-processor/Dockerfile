FROM apache/spark-py:v3.4.0

USER root

# Create a specific group and user with known IDs
RUN groupadd -g 1000 sparkgroup && \
    useradd -u 1000 -g 1000 -m -s /bin/bash sparkuser

# Create app and Ivy directories with correct permissions
RUN mkdir -p /app /tmp/.ivy2 && \
    chown -R sparkuser:sparkgroup /app /tmp/.ivy2

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=sparkuser:sparkgroup ./app .

# Switch to the named user
USER sparkuser
ENV HOME=/home/sparkuser

# Entrypoint remains the same, but we will pass config via Compose
CMD ["spark-submit", "main.py"]