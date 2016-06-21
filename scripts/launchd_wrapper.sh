#!/bin/bash

set -x

# brew install pyenv pyenv-virtualenv
if ! echo ":$PATH:" | grep -q ":/usr/local/bin:"; then
  PATH=$PATH:/usr/local/bin
fi

export PYENV_ROOT="$HOME/.pyenv"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# pyenv install --list
# pyenv install 3.5.1
# pyenv virtualenv 3.5.1 inotebook3
pyenv activate inotebook3
# pip install jupyter ipymd
# pip install matplotlib pandas
# brew install homebrew/science/hdf5
# pip install tables

startup () {
    echo "Starting ..."
    echo "PATH=$PATH"
    # jupyter notebook --help-all
    # jupyter notebook --generate-config
    jupyter notebook \
	--NotebookApp.ip='127.0.0.1' \
	--NotebookApp.port=9999 \
	--NotebookApp.open_browser=False \
	--NotebookApp.contents_manager_class='ipymd.IPymdContentsManager' \
	--NotebookApp.log_level='DEBUG' \
	# command end...

}

shutdown () {
    echo "Stoping ..."
    ps -ef | egrep "jupyter notebook [-]{2}" | awk '{print $2;}' | xargs -I {} kill -9 {}
    echo "Done"
}

## main ##
date
startup #()

# Allow any signal which would kill a process to stop it.
trap shutdown HUP INT QUIT ABRT KILL ALRM TERM TSTP

exit 0
