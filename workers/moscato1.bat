set packagebuilderhome=e:\packagebuilder

set PACKAGEBUILDER_RSAKEY=e:/packagebuilder/.packagebuilder.private_key.rsa


E:
cd e:\biocbld\bbs\%2\bioc\moscato1
call config.bat

E:
cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg




%BBS_PYTHON_CMD% builder.py %1