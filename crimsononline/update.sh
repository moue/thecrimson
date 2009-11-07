#!/bin/bash
set -e
set -x

svn update
python -m compileall . > /dev/null
sudo /etc/init.d/apache2 force-reload

