#!/bin/bash -e

script_dir=$(cd `dirname $0`; pwd)
root_dir=`dirname $script_dir`
tests_dir=$root_dir/tests

update_virtualenv()
{
    directory=$1
    requirements=$2

    [ -d "$directory" ] || virtualenv "$directory"
    source $directory/bin/activate
    pip install -r $requirements
}

update_virtualenv venv $tests_dir/requirements.txt

tox --recreate
$tests_dir/test_js.sh

deactivate
