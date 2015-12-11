echo "Activating virtual environment"
call env\Scripts\activate.bat

echo "Sourcing environment variables"
pushd workers
call moscato2.bat 3.3
popd

echo "Now starting server.py ..."
%BBS_PYTHON_CMD% -m workers.server > server.log 2>&1 &
echo "Server is started."
