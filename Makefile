# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: CC0-1.0

VENV?=.venv
ifeq ($(OS), Windows_NT)
	BIN?=$(VENV)\Scripts
else
	BIN?=$(VENV)/bin
endif
PYTHON?=$(VENV)/bin/python
PIP?=$(VENV)/bin/pip
PYTEST?=$(VENV)/bin/pytest

ifeq ($(OS), Windows_NT)
define delete_dir
	if exist $(1) rmdir /Q /s $(1)
endef
else
define delete_dir
	rm -fr $(1)
endef
endif

.PHONY: default
default:
	$(PYTEST) -vv tests/

# If virtualenv doesn't exist, create it, then fetch dependencies.
.PHONY: venv
venv:
	pip install virtualenv
ifeq ($(OS), Windows_NT)
	if NOT exist $(VENV) virtualenv $(VENV)
else
	[ -d $(VENV) ] || virtualenv $(VENV)
endif
	$(PIP) install -r requirements.txt
	$(PYTHON) setup.py install

.PHONY: clean
clean:
	python setup.py clean
	$(call delete_dir,build)
	$(call delete_dir,.venv)
