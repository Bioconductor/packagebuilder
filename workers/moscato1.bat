set packagebuilderhome=d:\packagebuilder

set PACKAGEBUILDER_RSAKEY=d:/packagebuilder/.packagebuilder.private_key.rsa


D:
cd d:\biocbld\bbs\%2\bioc\moscato1
call config.bat

D:
cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg


set BBS_R_HOME=D:\packagebuilder\R
set BBS_R_CMD=%BBS_R_HOME%\bin\R.exe


set TMPDIR=

%BBS_PYTHON_CMD% builder.py %1