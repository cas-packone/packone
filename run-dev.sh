#!/bin/bash
export LC_ALL='en_US.utf8'
nohup python -u manage.py runserver 0:8080 2>&1 &
# nohup python -u manage.py monitor-cloud 2>&1 &