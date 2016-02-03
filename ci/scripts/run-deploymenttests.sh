#!/bin/sh -e

TILE_DIR=$1
POOL_DIR=$2

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/deployment-tests" && pwd )"

cd "${POOL_DIR}"
python "${TEST_DIR}/pcf" products
