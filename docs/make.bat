@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

set PROJECT_DIR=snakeplane
set PROJECT_NAME=snakeplane


sphinx-build >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed.
	exit /b 1
)

if "%1" == "" (
    goto help
) else if "%1" == "help" (
    goto help
) else if "%1" == "clean" (
    goto clean
) else if "%1" == "pdf" (
    goto pdf
) else if "%1" == "html" (
    goto html
) else if "%1" == "latex" (
    goto latex
) else (
    echo.Error: Invalid parameter %1
    goto help
)

:help
    echo.Usage: make "[help | html | latex | pdf | clean]"
    goto end

:clean
    rmdir /s /q _build
    goto end

:html
:latex
    sphinx-apidoc -f -o source ../%PROJECT_DIR%
    sphinx-build -b %1 -c . source _build/%1
    goto end

:pdf
    sphinx-apidoc -f -o source ../%PROJECT_DIR%
    sphinx-build -b latex -c . source _build/latex
    pdflatex -output-directory=_build\pdf -include-directory=_build\latex _build\latex\%PROJECT_NAME%.tex
    goto end

:end
    popd