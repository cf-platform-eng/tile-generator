#!/bin/sh -e

TILE_DIR=$1
PCF_RESERVATION=$2

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/deployment-tests" && pwd )"

echo "name:"
echo
cat $2/name
echo
echo "metadata:"
echo
cat $/metadata