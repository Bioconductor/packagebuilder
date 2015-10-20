set packagebuilderhome=c:\packagebuilder

set PACKAGEBUILDER_RSAKEY=c:/packagebuilder/.packagebuilder.private_key.rsa


rem D:
cd c:\biocbld\bbs\%2\bioc\windows2.bioconductor.org
call config.bat

rem D:
cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg


set BBS_R_HOME=C:\packagebuilder\R
set BBS_R_CMD=%BBS_R_HOME%\bin\R.exe


set TMPDIR=

%BBS_PYTHON_CMD% builder.py %1