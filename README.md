# Cost Estimator

A Python application for cost estimation.

## Prerequisites

- Python 3.8 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- Docker (optional, for containerization)

---

## Setup Instructions

### 1. Install Poetry

If Poetry is not installed, you can install it using the following command:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Verify the installation:

```bash
poetry --version
```

### 2. Install Dependencies

Run the following command to install the project dependencies:

```bash
poetry install
```

This will create a virtual environment and install all dependencies specified in `pyproject.toml`.

### 3. Run the Application

To run the application within the Poetry environment:

```bash
poetry run python your_script.py
```

Replace `your_script.py` with the entry point of your application.

---

## Using the Makefile

If a `Makefile` is provided, you can use it to simplify common tasks. Below are some common commands:

- **Install Dependencies**:
  ```bash
  make install
  ```

- **Run Tests**:
  ```bash
  make test
  ```

- **Run the Application**:
  ```bash
  make run
  ```

---

## Docker Containerization

To containerize the application using Docker, follow these steps:

### 1. Build the Docker Image

Run the following command to build the Docker image:

```bash
docker build -t cost-estimator .
```

### 2. Run the Docker Container

Run the container using the following command:

```bash
docker run --rm -it cost-estimator
```

### 3. Access the Application

If the application exposes a web service or API, ensure the appropriate ports are mapped in the `Dockerfile` and use the container's IP address to access it.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.