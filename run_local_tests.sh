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

LOCAL_TEST_DIR='temp_local_test'
SCRIPT_REALPATH=`realpath $0`
SCRIPT_DIR=`dirname ${SCRIPT_REALPATH}`

command -v tile >/dev/null 2>&1 || { echo "Command 'tile' not found." >&2; exit 1; }

"${SCRIPT_DIR}"/ci/scripts/run-unittests.sh

rm -rf "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
mkdir "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"

if [ "$1" = "rebuild" ] || [ ! -e "${SCRIPT_DIR}"/sample/product/*.pivotal ]; then
    "${SCRIPT_DIR}"/ci/scripts/tile-build.sh "${SCRIPT_DIR}"/sample "${SCRIPT_DIR}"/sample "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
else
    echo "#######################################################"
    echo "# Using existing .pivotal file in sample/product/ dir #"
    echo "#######################################################"
    cp ${SCRIPT_DIR}/sample/product/*.pivotal "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
    cp ${SCRIPT_DIR}/sample/tile-history*.yml "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
fi

"${SCRIPT_DIR}"/ci/scripts/run-acceptancetests.sh "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"

rm -rf "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
