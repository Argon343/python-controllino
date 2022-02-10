<!--
# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH

SPDX-License-Identifier: GPL-3.0-or-later
-->

# python-controllino

[![CI (install, test)](https://github.com/maltekliemann/python-controllino/actions/workflows/linux.yaml/badge.svg)](https://github.com/maltekliemann/python-controllino/actions/workflows/linux.yaml)
[![REUSE license check](https://github.com/maltekliemann/python-controllino/actions/workflows/license.yaml/badge.svg)](https://github.com/maltekliemann/python-controllino/actions/workflows/license.yaml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

python-controllino is a python module for using serial devices that implement
the 8tronix Controllino Protocol.

For documentation, please refer to the docstrings in `src/controllino` or the
tests.

## Technical notes for devs

### Test Suite

Run `make venv && make` to create a virtual environment for testing and run the
test suite.

### Style guide

-   Our Python code follows the [Black](https://github.com/psf/black) style
    guide
-   The formatting of our Python docstrings follows
    [3.8 Comments and Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
    of the Google Python Style Guide
-   We use [prettier](https://prettier.io) to format markdown files
-   The Python code, specification and documentation is licensed under
    GPL-3.0-or-later, all examples are unlicensed; we follow the
    [REUSE-3.0 specification](https://reuse.software/spec/)

### Workflow

We use the standard
[gitflow](https://nvie.com/posts/a-successful-git-branching-model/) branching
model. Pull requests should only go into the `develop` branch. The `develop`
branch will be regularly merged into `master`.
