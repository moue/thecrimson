#!/bin/bash
set -e
set -x

svn update
sudo /etc/init.d/apache2 force-reload

