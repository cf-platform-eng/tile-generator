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

echo "Saving settings into ${BACKUP_FILE}"
python "${TEST_DIR}/pcf" backup "${BACKUP_DIR}/${BACKUP_FILE}"
echo
