# Use an official Spark image as a parent image
FROM apache/spark-py:v3.4.0

USER root

# Create a non-root user
RUN groupadd --system spark && useradd --system --gid spark spark

# Create app directory and change ownership
RUN mkdir -p /app && chown -R spark:spark /app

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and change ownership
COPY --chown=spark:spark ./app .

# Switch to the non-root user
USER spark

# Set the entrypoint to run the Spark application
CMD ["spark-submit", "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0", "main.py"]
