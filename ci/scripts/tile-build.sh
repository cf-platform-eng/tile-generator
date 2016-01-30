#!/bin/sh

SOURCE_DIR=$1
HISTORY_DIR=$2
TARGET_DIR=$3

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

cd ${BASE_DIR}

if [ -f "${HISTORY_DIR}/tile-history.yml" ]; then
	cp ${HISTORY_DIR}/tile-history.yml ${SOURCE_DIR}
fi
(cd ${SOURCE_DIR}; ${REPO_DIR}/tile build)
cp ${SOURCE_DIR}/product/*.pivotal ${TARGET_DIR}
cp ${SOURCE_DIR}/tile-history.yml ${HISTORY_DIR}