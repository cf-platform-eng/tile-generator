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

REPO_DIR="$( cd "$( dirname "$0" )/.." && pwd )"
LOCAL_TEST_DIR="${REPO_DIR}/temp_local_test"

"${REPO_DIR}/ci/scripts/run-unittests.sh"

rm -rf "${LOCAL_TEST_DIR}"
mkdir "${LOCAL_TEST_DIR}"

. "${REPO_DIR}/ci/scripts/setup-venv.sh"
"${REPO_DIR}/sample/src/build.sh"

if [ "$1" = "withcache" ]; then
    echo "########################################################"
    echo "# Building a new .pivotal file using cache option.     #"
    echo "########################################################"
    pushd "${REPO_DIR}/sample"
    mkdir -p cache
    tile build --cache cache
    cp product/*.pivotal "${LOCAL_TEST_DIR}"
    cp tile-history*.yml "${LOCAL_TEST_DIR}"
    popd
else
    echo "#############################################################"
    echo "# Creating a new .pivotal file. Use 'withcache' argument to #"
    echo "# build using the cache option for 'tile build'.            #"
    echo "#############################################################"
    "${REPO_DIR}"/ci/scripts/tile-build.sh "${REPO_DIR}"/sample "${REPO_DIR}"/sample "${LOCAL_TEST_DIR}"
fi

"${REPO_DIR}"/ci/scripts/run-acceptancetests.sh "${LOCAL_TEST_DIR}"

rm -rf "${LOCAL_TEST_DIR}"
