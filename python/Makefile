# define VENV_NAME to use a specific virtual environment. It defaults to `env`.
VENV_NAME?=env
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=python3
# a placeholder for the VENV target
VENV =

# check if the VENV file exists
ifneq ("$(wildcard $(PVENV_ACTIVATE))","")
    VENV = venv
    PYTHON = ${VENV_NAME}/bin/python3
endif

default: docstyle flake8 test

venv: $(VENV_NAME)/bin/activate

test: $(VENV)
	${PYTHON} -m pytest --doctest-modules

docstyle: $(VENV)
	${PYTHON} -m pydocstyle ./ ./test

flake8: $(VENV)
    # E722 Do not use bare except, specify exception instead https://www.flake8rules.com/rules/E722.html
    # F401 Module imported but unused   https://www.flake8rules.com/rules/F401.html
    # F403 'from module import *' used; unable to detect undefined names  https://www.flake8rules.com/rules/F403.html
    # W503 Line break occurred before a binary operator https://www.flake8rules.com/rules/W503.html
    # E501 Line too long (>79 characters) https://www.flake8rules.com/rules/E501.html
	${PYTHON} -m flake8 ./ test/  --count --ignore=E501 --show-source --statistics --doctests --exclude ".venv" --format pylint

autopep8: $(VENV)
	${PYTHON} -m autopep8 --max-line-length 120 -i *.py test/*.py

coverage: $(VENV)
	${PYTHON} -m pytest test --doctest-modules --junitxml=junit/test-results.xml --cov=notecard --cov-report=xml --cov-report=html

requirements: $(VENV)
	${PYTHON} -m pip install -r requirements.txt -r requirements-test.txt

# run_build: $(VENV)
#	${PYTHON} -m setup sdist bdist_wheel

# deploy: $(VENV)
#	${PYTHON} -m twine upload -r "pypi" --config-file .pypirc 'dist/*'

.PHONY: venv test coverage run_build deploy autopep8
