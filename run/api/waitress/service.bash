#!/bin/bash

fileRoot=$(realpath "$0" | sed 's|\(.*\)/.*|\1|')
cd $fileRoot || exit
cd ../../..

exec venv/bin/python run/api/waitress/runserver.py