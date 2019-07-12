#!/bin/sh -e

# tile-generator
#
# Copyright (c) 2015-Present Pivotal Software, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

TILE_DIR=$1

# Cleanup previous run
rm -rf ${TILE_DIR}/product
rm -rf ${TILE_DIR}/release

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

mkdir product && ( cd product && unzip "../${TILE_FILE}" )

BOSH_FILE=`ls product/releases/test-tile-*.tgz`
if [ -z "${BOSH_FILE}" ]; then
	echo "No match for releases/test-tile-*.tgz"
	exit 1
fi

mkdir release && ( cd release && gunzip -c "../${BOSH_FILE}"  | tar xf - )

for TGZ_FILE in release/*/*.tgz
do
	TGZ_DIR=`echo "${TGZ_FILE}" | sed "s/\.tgz\$//"`
	mkdir -p "${TGZ_DIR}"
	( cd "${TGZ_DIR}"; gunzip -c "../../../${TGZ_FILE}" | tar xf - )
	# Remove tar file so we don't get double counts in tests
	rm "${TGZ_FILE}"
done

python -m unittest discover -v -s ${TEST_DIR} -p '*_acceptancetest.py'
