#!/usr/bin/env bash
BASE_DIR=`pwd`
NAME=$(basename $BASE_DIR)
if [[ "$NAME" != "persist-queue" ]];then
    echo "must run this in project root"
    exit 1
fi
python setup.py build sdist
python setup.py build bdist_wheel
twine upload ${BASE_DIR}/dist/*
