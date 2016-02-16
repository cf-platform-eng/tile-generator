#!/bin/sh -e

POOL_DIR="$( cd "$1" && pwd )"
BACKUP_DIR="$( cd "$2" && pwd )"

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
BIN_DIR="$( cd "${REPO_DIR}/bin" && pwd )"

PCF="${BIN_DIR}/pcf"

PCF_NAME=`cat "${POOL_DIR}/name"`
if [ -z "${PCF_NAME}" ]; then
	echo "No pcf environment has been claimed"
	exit 1
fi

FLAG_FILE="pcf-backup-${PCF_NAME}-0.0.0.yml"
BACKUP_FILE="pcf-backup-${PCF_NAME}-0.0.1.yml"

cd "${POOL_DIR}"

if [ "$3" -eq "init" ]; then
	echo "Initializing ${PCF_NAME} for backup"
	touch "${BACKUP_DIR}/${FLAG_FILE}"
	echo
	exit 0
fi

if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
	echo "Backup ${BACKUP_FILE} already exists"
	echo
	exit 0
fi

echo "Backing up to ${BACKUP_FILE}"
$PCF backup "${BACKUP_DIR}/${BACKUP_FILE}"
echo
