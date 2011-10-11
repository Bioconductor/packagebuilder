set packagebuilderhome=c:\packagebuilder

set PACKAGEBUILDER_RSAKEY=c:/packagebuilder/.packagebuilder.private_key.rsa


cd c:\biocbuild\BBS\%2\bioc\cyclonus
call config.bat

cd %packagebuilderhome%

set BBS_USER=pkgbuild
set SVN_USER=pkgbuild
set SVN_PASS=buildpkg


set BBS_HOME=c:\biocbuild\BBS

%BBS_PYTHON_CMD% builder.py %1