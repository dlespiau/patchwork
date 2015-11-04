#!/bin/sh -e

script_dir=$(cd `dirname $0`; pwd)
root_dir=`dirname $script_dir`
tests=$root_dir/tests

$tests/test_jshint.sh
$tests/test_karma.sh
