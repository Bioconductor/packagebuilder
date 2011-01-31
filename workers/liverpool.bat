set packagebuilderhome=e:\packagebuilder
E:
cd e:\biocbld\bbs\%2\bioc\liverpool
call config.bat

E:
cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg

set BBS_RSAKEY=e:\pkgbuild\packagebuilder\.packagebuilder.private_key.rsa
set RSAKEY=e:\pkgbuild\packagebuilder\.packagebuilder.private_key.rsa



%BBS_PYTHON_CMD% builder.py %1