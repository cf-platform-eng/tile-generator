#!/bin/bash -e

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
SRC_DIR="$( cd "${MY_DIR}" && pwd )"
APP_DIR="$( cd "${SRC_DIR}/app" && pwd )"
BUILDPACK_DIR="$( cd "${SRC_DIR}/buildpack" && pwd )"
RESOURCES_DIR="$( cd "${SRC_DIR}/../resources" && pwd )"

cd "${APP_DIR}"
mkdir -p vendor
pip install --download vendor -r requirements.txt
zip -r "${RESOURCES_DIR}/app.zip" *

cd "${BUILDPACK_DIR}"
zip -r "${RESOURCES_DIR}/buildpack.zip" *
