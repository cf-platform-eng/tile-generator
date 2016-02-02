#!/bin/sh -e

TILE_DIR=$1

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/acceptance-tests" && pwd )"

cd ${TILE_DIR}

TILE_FILE=`ls *.pivotal`
if [ -z "${TILE_FILE}" ]; then
	echo "No match for *.pivotal"
	exit 1
fi

mkdir product && (cd product && unzip "../${TILE_FILE}")

BOSH_FILE=`ls product/releases/test-tile-*.tgz`
if [ -z "${BOSH_FILE}" ]; then
	echo "No match for releases/test-tile-*.tgz"
	exit 1
fi

mkdir release && (cd release && tar xvf "../${BOSH_FILE}")

for TGZ_FILE in release/*/*.tgz
do
	TGZ_DIR=`echo "${TGZ_FILE}" | sed "s/\.tgz\$//"`
	TAR_FILE="${TGZ_DIR}.tar"
	mkdir -p "${TGZ_DIR}"
	(cd "${TGZ_DIR}"; gunzip "../../../${TGZ_FILE}"; tar xvf "../../../${TAR_FILE}")
	rm "${TAR_FILE}"
done

python -m unittest discover -v -s ${TEST_DIR} -p '*_acceptancetest.py'
