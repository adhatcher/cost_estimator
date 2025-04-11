.PHONY: install build test coverage run package

install:
	poetry install

build:
	poetry build

test:
	PYTHONPATH=./ poetry run pytest

coverage:
	poetry run pytest --cov=cost_estimator

run:
	PYTHONPATH=cost_estimator FLASK_APP=cost_estimator.app poetry run flask run --host=0.0.0.0 --port=8000

# Target to package the application as a .whl file
package:
	poetry build -f wheel
