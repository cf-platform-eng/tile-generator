#!/bin/bash -e

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
pip install --download vendor -r requirements.txt
zip -r "${RESOURCES_DIR}/app.zip" *

cd "${BUILDPACK_DIR}"
zip -r "${RESOURCES_DIR}/buildpack.zip" *
