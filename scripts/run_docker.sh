#!/bin/bash

set -x

docker run \
    --interactive --tty --rm \
    -v $PWD:/home/jovyan/work \
    -p 8888:8888 \
    jupyter/datascience-notebook start-notebook.sh
