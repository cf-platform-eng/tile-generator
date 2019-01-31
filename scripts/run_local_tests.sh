#!/bin/bash -e

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
SCRIPT_DIR="$( cd "$( dirname "$0" )/.." && pwd )"
VENV="$SCRIPT_DIR/tile-generator-env"
deactivate >/dev/null 2>&1 || echo ''
rm -rf $VENV
echo "Creating a new virtual environment..."
virtualenv -q -p python2 $VENV
source $VENV/bin/activate
pip install -e .
source $VENV/bin/activate

command -v tile >/dev/null 2>&1 || { echo "Command 'tile' not found." >&2; exit 1; }

"${SCRIPT_DIR}"/ci/scripts/run-unittests.sh

rm -rf "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
mkdir "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"

"${SCRIPT_DIR}"/sample/src/build.sh

if [ "$1" = "withcache" ]; then
    echo "########################################################"
    echo "# Building a new .pivotal file using cache option.     #"
    echo "########################################################"
    pushd ${SCRIPT_DIR}/sample
    mkdir -p cache
    tile build --cache cache
    cp product/*.pivotal "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
    cp tile-history*.yml "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
    popd
else
    echo "#############################################################"
    echo "# Creating a new .pivotal file. Use 'withcache' argument to #"
    echo "# build using the cache option for 'tile build'.            #"
    echo "#############################################################"
    "${SCRIPT_DIR}"/ci/scripts/tile-build.sh "${SCRIPT_DIR}"/sample "${SCRIPT_DIR}"/sample "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
fi

"${SCRIPT_DIR}"/ci/scripts/run-acceptancetests.sh "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"

rm -rf "${SCRIPT_DIR}"/"${LOCAL_TEST_DIR}"
