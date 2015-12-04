#!/bin/sh -e

script_dir=$(cd `dirname $0`; pwd)
root_dir=`dirname $script_dir`
patchwork=$root_dir/patchwork

files=$(cat <<-END
    $patchwork/bin/parsemail.py
    $patchwork/admin.py
END
)

tox -e pep8 $files
