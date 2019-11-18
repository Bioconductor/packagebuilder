
cd /d "%~dp0"

@rem call not supported anymore
@rem call env\Scripts\activate.bat
@rem when run interactively used the following
.\env\Scripts\activate

set BBS_PYTHON_CMD=C:\Python37\python.exe

python workers\cleanUpIssues.py
