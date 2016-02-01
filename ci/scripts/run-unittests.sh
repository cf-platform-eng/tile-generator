#!/bin/sh -e

UNITTEST_DIR=$1

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

cd ${BASE_DIR}

python -m unittest discover -v -s ${UNITTEST_DIR} -p '*_unittest.py'
