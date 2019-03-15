# Alteryx SnakePlane Source Code Documentation
This page describes how to build the source code documentation for the `snakeplane` package using [Sphinx](http://www.sphinx-doc.org/en/master/).

## Installation
The documentation depends on the following additional Python packages and/or applications being installed.

* Python Development Packages
* [PlantUML](http://plantuml.com/)
* [Graphviz](https://graphviz.gitlab.io/)
* [MiKTeX](https://miktex.org/download)

### Python Development Packages
To build the Sphinx documentation additional Python packages must first be installed, which are listed in `requirements-dev.txt`

The Python package dependencies for building the `snakeplane` Documentation can be installed using `pip`
```
pip install -r requirements-dev.txt
```

### Install PlantUML, MikTex and Graphviz
PlantUML is used to render domain model, sequence diagrams, and other diagrams.
MikTex is used to create a Latex document from which a PDF can be created.
Graphviz is used to render graphs in PlanUML.

The best way to install `PlantUML`, `MiKTeX` and `Graphviz` on Windows is using [Chocolatey](https://chocolatey.org/).
After installing `Chocolatey` run the following:

```
choco install plantuml
choco install miktex
```

## Building
A `make.bat` in `./docs` for building the Sphinx documentation has been provided.

### Build html docs
To build the html documentation execute the following commands:
```
make html
```

1. [sphinx-apidoc](http://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html): Builds the [reStructuredText](http://docutils.sourceforge.net/rst.html) files under `_build/source`.
2. [sphinx-build](http://www.sphinx-doc.org/en/master/man/sphinx-build.html): Builds the final documentation under `_build`.

### Build pdf documentation
```MikTeX``` and ```pdflatex``` are used to build pdf documentation.

To build the pdf documentation execute the following commands:
```
make pdf
```

## Viewing documentation
* Assuming that you've successfully built the html documentation, it should be located at, [_build/html/index.html](_build/html/index.html)
* The pdf documentation will be at [_build/pdf/snakeplane.pdf](_build/pdf/snakeplane.pdf)

## Clean the build
```
make clean
```