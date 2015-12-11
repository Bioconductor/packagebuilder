set packagebuilderhome=e:\packagebuilder

set PACKAGEBUILDER_RSAKEY=e:/packagebuilder/.packagebuilder.private_key.rsa


E:
cd e:\biocbld\bbs\%1\bioc\moscato2
call config.bat

E:
cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg

set BBS_R_HOME=E:\packagebuilder\R
set BBS_R_CMD=%BBS_R_HOME%\bin\R.exe
