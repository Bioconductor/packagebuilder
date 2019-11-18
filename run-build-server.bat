echo "Changing to packagebuilder directory"
cd /d "%~dp0"
echo "New working directory is "
echo %cd%

echo "Activating virtual environment"
@rem call env\Scripts\activate.bat
@rem call not supported anymore
@rem Interactively initialized with the following:
.\env\Scripts\activate

@rem ALL OF THESE ARE SET IN PROPERTIES FILES/SERVER.py
set BBS_PYTHON_CMD=C:\Python37\python.exe
@rem set BBS_RSYNC_CMD=C:\cygwin\bin\rsync.exe
@rem With StrictHostKeyChecking=no, ssh will automatically add new host keys
@rem to the user known hosts files (so it doesn't get stalled waiting for an
@rem answer when not run interactively).
@rem set BBS_SSH_CMD=%BBS_SSH_CMD% -qi %BBS_RSAKEY% -o StrictHostKeyChecking=no
@rem set BBS_RSYNC_CMD=%BBS_RSYNC_CMD% -r --delete --exclude='.svn'
@rem set BBS_RSYNC_RSH_CMD=%BBS_RSYNC_CMD% -e '%BBS_SSH_CMD%'
@rem set BBS_CENTRAL_BASEURL=http://zin2/BBS/%BBS_BIOC_VERSIONED_REPO_PATH%

echo "Now starting server.py ..."
@rem Interactively just use python not BBS_PYTHIN_CMD
@rem %BBS_PYTHON_CMD% -m workers.server > server.log 2>&1
python -m workers.server >> server.log 2>&1
echo "Server is started."
