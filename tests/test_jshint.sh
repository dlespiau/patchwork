#!/bin/sh -e

script_dir=$(cd `dirname $0`; pwd)
root_dir=`dirname $script_dir`
js=$root_dir/htdocs/js
tests=$root_dir/tests
files="$js/patchwork.js $js/common.js $js/bundle.js $tests/test_*.js"

jshint $files
