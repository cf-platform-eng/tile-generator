#!/bin/sh

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

cd ${BASE_DIR}
cd $1
${REPO_DIR}/tile build
cp $1/product/*.pivotal $2