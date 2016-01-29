#!/bin/bash -eux

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

pushd ${BASE_DIR}
	pushd $1
		${REPO_DIR}/tile build
	popd
popd
