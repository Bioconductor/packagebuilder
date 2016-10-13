
cd /d "%~dp0"

call env\Scripts\activate.bat

set BBS_PYTHON_CMD=C:\Python27\python.exe

python workers\cleanUpIssues.py
