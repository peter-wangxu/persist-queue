#!/usr/bin/env bash
set -e
BASE_DIR=`pwd`
NAME=$(basename $BASE_DIR)
if [[ "$NAME" != "persist-queue" ]];then
    echo "must run this in project root"
    exit 1
fi
python setup.py build sdist
python setup.py build bdist_wheel
twine check ${BASE_DIR}/dist/*.tar.gz
twine check ${BASE_DIR}/dist/*.whl
twine upload ${BASE_DIR}/dist/*
