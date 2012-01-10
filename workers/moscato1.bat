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




%BBS_PYTHON_CMD% builder.py %1