echo "Changing to LaTex test directory"
cd /d "%~dp0"
cd test
echo "New working directory is "
echo %cd%

echo "Activating virtual environment"
call env\Scripts\activate.bat

set BBS_R_CMD=E:\packagebuilder\R\bin\R.exe

echo "Now building SPBTestLatex..."
%BBS_R_CMD% CMD build SPBTestLatex > latex_test.log 2>&1
echo "SPBTestLatex is built."
