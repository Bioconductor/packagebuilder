set packagebuilderhome=c:\packagebuilder

set PACKAGEBUILDER_RSAKEY=c:/packagebuilder/.packagebuilder.private_key.rsa


cd c:\biocbld\bbs\%2\bioc\liverpool
call config.bat

cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg


set BBS_HOME=c:\biocbld\BBS

%BBS_PYTHON_CMD% builder.py %1