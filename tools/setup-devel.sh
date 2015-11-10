#!/bin/sh
# Patchwork - automated patch tracking system
# Copyright (C) 2015 Intel Corporation
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


CFG=patchwork.settings.dev-sqlite

update_virtualenv()
{
    directory=$1
    requirements=$2

    [ -d "$directory" ] || virtualenv "$directory"
    . $directory/bin/activate
    pip install --upgrade -r $requirements
}

cd $(dirname $0)/..

update_virtualenv venv docs/requirements-dev-sqlite.txt
export DJANGO_SETTINGS_MODULE=$CFG
./manage.py migrate --noinput
./manage.py loaddata test_data
deactivate
