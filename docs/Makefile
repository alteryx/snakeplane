# Makefile for Sphinx documentation

clean:
	rm -rf _build

%: Makefile
	sphinx-apidoc -f -o source ../snakeplane
	sphinx-build -b $@ -c . source _build/html
