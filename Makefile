# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: CC0-1.0

VENV?=.venv
PYTHON?=$(VENV)/bin/python
PIP?=$(VENV)/bin/pip
PYTEST?=$(VENV)/bin/pytest

.PHONY: default
default: venv
	$(PYTEST) -vv tests/

.PHONY: venv
venv:
	pip install virtualenv
	# If virtualenv doesn't exist, create it, then fetch dependencies.
	[ -d $(VENV) ] || virtualenv $(VENV)
	$(PIP) install -r requirements.txt
	$(PYTHON) setup.py install

.PHONY: sphinx
sphinx:
	sphinx-apidoc --force --private --separate -o docs/source src/pylab
	cd docs/ && make html

.PHONY: clean
clean:
	rm -fr build
	rm -fr .venv

.PHONY: install
install:
	python setup.py install
