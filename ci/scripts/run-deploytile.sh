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

TILE_DIR="$( cd "$1" && pwd )"
POOL_DIR="$( cd "$2" && pwd )"

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"

PCF="pcf"

NETWORK="$(jq -r .ert_subnet $POOL_DIR/metadata)"
if [ -n "$NETWORK" ]; then
	NETWORK="--network $NETWORK"
fi

TILE_FILE=`cd "${TILE_DIR}"; ls *.pivotal`
if [ -z "${TILE_FILE}" ]; then
	echo "No files matching ${TILE_DIR}/*.pivotal"
	ls -lR "${TILE_DIR}"
	exit 1
fi

PRODUCT=`echo "${TILE_FILE}" | sed "s/-[0-9].*$//"`
VERSION=`echo "${TILE_FILE}" | sed "s/${PRODUCT}-//" | sed "s/\.pivotal\$//"`

cd "${POOL_DIR}"

echo "Enable diego_docker:"
$PCF target -o system -s system
cf enable-feature-flag diego_docker

echo "Available products:"
$PCF products
echo

echo "Uploading ${TILE_FILE}"
$PCF import "${TILE_DIR}/${TILE_FILE}"
echo

echo "Available products:"
$PCF products
$PCF is-available "${PRODUCT}" "${VERSION}"
echo

echo "Installing product ${PRODUCT} version ${VERSION}"
$PCF install "${PRODUCT}" "${VERSION}"
echo

echo "Available products:"
$PCF products
$PCF is-installed "${PRODUCT}" "${VERSION}"
echo

echo "Configuring product ${PRODUCT}"
$PCF configure --skip-validation "${PRODUCT}" ${NETWORK} "${REPO_DIR}/sample/missing-properties.yml"
echo

echo "Applying Changes"
$PCF apply-changes --product "${PRODUCT}" --deploy-errands deploy-meta-buildpack,deploy-all,acceptance-tests --delete-errands ''
echo
