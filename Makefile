# Variables
APP_NAME = cost_estimator
ENTRY_POINT = cost_estimate/app.py
HOST = 0.0.0.0
PORT = 8000
FLASK_APP = $(APP_NAME).app


.PHONY: install build test coverage run package clean

install:
	poetry install

# Define the build target to create a Python wheel
build:
	poetry build -f wheel


run:
	PYTHONPATH=${APP_NAME} FLASK_APP=${FLASK_APP} poetry run flask run --host=${HOST} --port=${PORT}

# Target to package the application as a .whl file
package:
	poetry build -f wheel

# Clean up build artifacts
clean:
	rm -rf build dist *.egg-info
