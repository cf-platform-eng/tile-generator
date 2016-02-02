#!/bin/sh -e

TILE_DIR=$1

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/acceptance-tests" && pwd )"

cd ${TILE_DIR}
python -m unittest discover -v -s ${TEST_DIR} -p '*_acceptancetest.py'
