#!/bin/sh -e

TILE_DIR=$1
POOL_DIR=$2

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/deployment-tests" && pwd )"

cd "${BASE_DIR}"

TILE_FILE=`cd "${TILE_DIR}"; ls *.pivotal`
if [ -z "${FILE_FILE}" ]; then
	echo "No files matching ${TILE_DIR}/*.pivotal"
	ls -lR "${TILE_DIR}"
	exit 1
fi

cd "${POOL_DIR}"

echo "available products:"
python "${TEST_DIR}/pcf" products
echo

echo "uploading ${TILE_FILE}"
python "${TEST_DIR}/pcf" import "${TILE_DIR}/${TILE_FILE}"
echo
