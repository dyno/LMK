SHELL = /bin/bash

ifndef VIRTUAL_ENV
WITH_VENV := poetry run
else
WITH_VENV :=
endif

PYTHON := $(WITH_VENV) python3

PROJECT := lmk

.DEFAULT_GOAL := run

# ----------------------------------------------------------------------
init: poetry-install install-ipykernel install-labextensions

poetry-install:
	poetry install

poetry-update:
	poetry update

install-ipykernel:
	$(PYTHON) -m ipykernel install     \
		--user                           \
		--name $(PROJECT)-python         \
		--display-name $(PROJECT)-python \
	# END

install-labextensions:
	$(WITH_VENV) jupyter labextension install \
		@jupyter-widgets/jupyterlab-manager     \
		@jupyterlab/toc                         \
		jupyterlab-jupytext                     \
		nbdime-jupyterlab                       \
	# END

# ------------------------------------------------------------------------------
test:
	$(WITH_VENV) run pytest

jupyter:
	$(WITH_VENV) jupyter lab                                                  \
	  --NotebookApp.open_browser=False                                        \
	  --NotebookApp.port=8038                                                 \
	  --NotebookApp.contents_manager_class="jupytext.TextFileContentsManager" \
	# END

# ----------------------------------------------------------------------
run-docker: docker-run
docker-run:
	docker run                                         \
			--interactive --tty --rm                       \
			-v $${PWD}:/home/jovyan/work                   \
			-p 8888:8888                                   \
			jupyter/datascience-notebook start-notebook.sh \
	# END
