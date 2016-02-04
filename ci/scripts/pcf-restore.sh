#!/bin/sh -e

POOL_DIR="$( cd "$1" && pwd )"
BACKUP_DIR="$( cd "$2" && pwd )"

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/deployment-tests" && pwd )"

PCF_NAME=`cat "${POOL_DIR}/name"`
if [ -z "${PCF_NAME}" ]; then
	echo "No pcf environment has been claimed"
	exit 1
fi

BACKUP_FILE="pcf-backup-${PCF_NAME}-0.0.0.yml"

cd "${POOL_DIR}"

echo "Available products:"
python "${TEST_DIR}/pcf" products
echo

echo "Restoring settings from ${BACKUP_FILE}"
python "${TEST_DIR}/pcf" restore "${BACKUP_DIR}/${BACKUP_FILE}"
echo

echo "Available products:"
python "${TEST_DIR}/pcf" products
echo

echo "Deleting unused products"
python "${TEST_DIR}/pcf" delete-unused-products
echo

echo "Available products:"
python "${TEST_DIR}/pcf" products
echo
