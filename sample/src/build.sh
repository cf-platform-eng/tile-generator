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

BUILD_DIR="$1"
MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
SAMPLE_DIR="$( cd "${MY_DIR}/.." && pwd )"

if [ -n "${BUILD_DIR}" ]; then
	cp -r "${SAMPLE_DIR}"/* "${BUILD_DIR}"
	SAMPLE_DIR="${BUILD_DIR}"
fi

SRC_DIR="$( cd "${SAMPLE_DIR}/src" && pwd )"
APP_DIR="$( cd "${SRC_DIR}/app" && pwd )"
BUILDPACK_DIR="$( cd "${SRC_DIR}/buildpack" && pwd )"
RESOURCES_DIR="$( cd "${SAMPLE_DIR}/resources" && pwd )"

cd "${APP_DIR}"
mkdir -p vendor
pip install --no-binary :all: --download vendor -r requirements.txt
zip -r "${RESOURCES_DIR}/app.zip" *

cd "${BUILDPACK_DIR}"
zip -r "${RESOURCES_DIR}/buildpack.zip" *
