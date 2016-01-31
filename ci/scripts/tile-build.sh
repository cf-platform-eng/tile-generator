#!/bin/sh

SOURCE_DIR=$1
HISTORY_DIR=$2
TARGET_DIR=$3

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

cd ${BASE_DIR}

HISTORY=`ls ${HISTORY_DIR}/tile-history-*.yml`
if [ -n "${HISTORY}" ]; then
	echo "using history ${HISTORY}"
	cp ${HISTORY} ${SOURCE_DIR}/tile-history.yml
fi

(cd ${SOURCE_DIR}; ${REPO_DIR}/tile build)

VERSION=`grep '^version:' ${SOURCE_DIR}/tile-history.yml | sed 's/^version: //'`
HISTORY="tile-history-${VERSION}.yml"
echo "saving history ${HISTORY}"

cp ${SOURCE_DIR}/product/*.pivotal ${TARGET_DIR}
cp ${SOURCE_DIR}/tile-history.yml ${TARGET_DIR}/tile-history-${VERSION}.yml