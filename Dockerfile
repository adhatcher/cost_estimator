# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy only the necessary files for dependency installation
COPY pyproject.toml poetry.lock /app/

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Copy the wheel file into the container
COPY dist/*.whl /app/

# Install the wheel
RUN pip install --no-cache-dir /app/*.whl

# Copy the rest of the application code into the container
COPY . /app/

# Expose the port the app runs on (if applicable)
EXPOSE 5000

# Define the command to run the application
CMD ["python", "app.py"]
