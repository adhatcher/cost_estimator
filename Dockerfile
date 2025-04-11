FROM python:3.10-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy Poetry files and install dependencies
COPY pyproject.toml poetry.lock /app/
RUN poetry config virtualenvs.create false && poetry install --no-dev

# Copy application code
COPY . /app

# Set the default command to run the Flask app
CMD ["poetry", "run", "flask", "run", "--host=0.0.0.0", "--port=5000"]
