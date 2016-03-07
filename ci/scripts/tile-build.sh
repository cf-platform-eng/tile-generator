#!/bin/sh -e

SOURCE_DIR=$1
HISTORY_DIR=$2
TARGET_DIR=$3
DOCKER_DIR=$4

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
BIN_DIR="$( cd "${REPO_DIR}/bin" && pwd )"

TILE="${BIN_DIR}/tile"

cd ${BASE_DIR}

HISTORY=`ls ${HISTORY_DIR}/tile-history-*.yml`
if [ -n "${HISTORY}" ]; then
	cp ${HISTORY} ${SOURCE_DIR}/tile-history.yml
fi

if [ -n "${DOCKER_DIR}" ]; then
	DOCKER_DIR="--docker-cache $DOCKER_DIR"
fi

(cd ${SOURCE_DIR}; $TILE build $DOCKER_DIR )

VERSION=`grep '^version:' ${SOURCE_DIR}/tile-history.yml | sed 's/^version: //'`
HISTORY="tile-history-${VERSION}.yml"

cp ${SOURCE_DIR}/product/*.pivotal ${TARGET_DIR}
cp ${SOURCE_DIR}/tile-history.yml ${TARGET_DIR}/tile-history-${VERSION}.yml