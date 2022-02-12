#!/bin/bash

fileRoot=$(realpath "$0" | sed 's|\(.*\)/.*|\1|')
cd $fileRoot || exit
cd ../../..

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec venv/bin/gunicorn Rpi.wsgi:application --config run/api/gunicorn/conf.py