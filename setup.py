#!/usr/bin/env python
from setuptools import setup, find_packages
from snakeplane.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="SnakePlane",
    url="https://github.com/alteryx/snakeplane",
    license="Apache License 2.0",
    version=__version__,
    python_requires=">=3.6.0",
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="The Alteryx Python SDK Abstraction Layer",
    author="Alteryx",
    author_email="awalden@alteryx.com",
    install_requires=["numpy==1.16.0", "xmltodict==0.11.0"],
    packages=find_packages(),
)
