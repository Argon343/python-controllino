REM SPDX-FileCopyrightText: 2021 Forschungs- und Entwicklungszentrum Fachhochschule Kiel GmbH
REM
REM SPDX-License-Identifier: CC0-1.0

SET VENV=.venv
SET PYTHON=%VENV%\Scripts\python.exe
SET PIP=%VENV%\Scripts\pip.exe
SET PYTEST=%VENV%\Scripts\pytest.exe

IF /I "%1"=="default" GOTO default
IF /I "%1"=="venv" GOTO venv
IF /I "%1"=="sphinx" GOTO sphinx
IF /I "%1"=="clean" GOTO clean
IF /I "%1"=="install" GOTO install
GOTO error

:default
	CALL make.bat venv
	. %VENV%\Scripts\activate && pytest -vv tests\ && deactivate
	GOTO :EOF

:venv
	pip install virtualenv

	if NOT exist %VENV% virtualenv %VENV%
	%PIP% install -r requirements.txt
	%PYTHON% setup.py install
	GOTO :EOF

:sphinx
	sphinx-apidoc --module-first --force --private --separate -o docs/build src
	PUSHD docs && make html && POPD
	GOTO :EOF

:clean
	if exist build rmdir /Q /s build
	if exist %VENV% rmdir /Q /s %VENV%
	if exist docs\build rmdir /Q /s docs\build
	GOTO :EOF

:install
	python setup.py install
	GOTO :EOF

:error
    IF "%1"=="" (
        ECHO make: *** No targets specified and no makefile found.  Stop.
    ) ELSE (
        ECHO make: *** No rule to make target '%1%'. Stop.
    )
    GOTO :EOF

