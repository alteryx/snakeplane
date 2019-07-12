#!/usr/bin/env python
from setuptools import setup, find_packages
from snakeplane.version import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()




setup(
    name="SnakePlane",
    license="Apache License 2.0",
    version=__version__,
    python_requires='>=3.6.0',
    long_description=long_description,
    long_description_content_type="text/markdown",
    description="The Alteryx Python SDK Abstraction Layer",
    author="Alteryx",
    author_email="awalden@alteryx.com",
    package_dir={"": "snakeplane"},
    install_requires=[
        "xmltodict==0.11.0",
        "numpy==1.16.0",
        "pandas==0.23.4",
        "dateparser==0.7.0"
    ],
)