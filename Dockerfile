# Use an official Python runtime as a parent image
FROM python:3.12-slim

LABEL maintainer="Aaron Hatcher <aaron@aaronhatcher.com>"
LABEL description="Flask application to create cost estimates to compare ECS to EKS based on average pod CPU/Memory requirements and varying # of pods."


# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files for dependency installation
COPY pyproject.toml poetry.lock .
COPY cost_estimator/ ./cost_estimator/
COPY Makefile .


# Install Poetry
RUN pip install --no-cache-dir poetry \
 && poetry install --only main --no-root 

 
ENV PYTHONPATH=cost_estimator 
ENV FLASK_APP=cost_estimator.app
ENV PORT=8000
ENV HOST=0.0.0.0

# Expose the port the app runs on (if applicable)
EXPOSE $PORT

# Define the command to run the application
CMD ["poetry run flask run --host=${HOST} --port=${PORT}"]







