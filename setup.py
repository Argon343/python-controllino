# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: CC0-1.0

import setuptools

with open("README.md") as readme:
    long_description = readme.read()

setuptools.setup(
    name="python-controllino",
    version="0.1.3",
    author="Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH",
    description="Python API for USB devices running 8tronix Controllino Protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL-3.0-or-later",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
)
