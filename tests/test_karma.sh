#!/bin/sh -e

script_dir=$(cd `dirname $0`; pwd)
root_dir=`dirname $script_dir`
tests=$root_dir/tests

karma start $tests/karma.conf.js --single-run
