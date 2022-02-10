# SPDX-FileCopyrightText: 2021 8tronix GmbH, Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
#
# SPDX-License-Identifier: CC0-1.0

import setuptools

with open("README.md") as readme:
    long_description = readme.read()

setuptools.setup(
    name="pycontrollino",
    version="0.1.2",
    author="M. Kliemann",
    author_email="mail@maltekliemann.com",
    description="Python API for USB devices running 8tronix controllino protocol",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL v3.0",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 1",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=["pyserial>=3.5b0"],
)
