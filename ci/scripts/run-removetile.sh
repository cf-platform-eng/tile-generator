#!/bin/sh -e

TILE_DIR="$( cd "$1" && pwd )"
POOL_DIR="$( cd "$2" && pwd )"

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
BIN_DIR="$( cd "${REPO_DIR}/bin" && pwd )"

PCF="${BIN_DIR}/pcf"

TILE_FILE=`cd "${TILE_DIR}"; ls *.pivotal`
if [ -z "${TILE_FILE}" ]; then
	echo "No files matching ${TILE_DIR}/*.pivotal"
	ls -lR "${TILE_DIR}"
	exit 1
fi

PRODUCT=`echo "${TILE_FILE}" | sed "s/-[^-]*$//"`
VERSION=`echo "${TILE_FILE}" | sed "s/.*-//" | sed "s/\.pivotal\$//"`

cd "${POOL_DIR}"

echo "Available products:"
$PCF products
echo

if ! $PCF is-installed "${PRODUCT}" ; then
	echo "${PRODUCT} not installed - skipping removal"
	exit 0
fi

echo "Uninstalling ${PRODUCT}"
$PCF uninstall "${PRODUCT}"
echo

echo "Applying Changes"
$PCF apply-changes
echo

echo "Available products:"
$PCF products
echo

if $PCF is-installed "${PRODUCT}" ; then
	echo "${PRODUCT} remains installed - remove failed"
	exit 1
fi

exit 0 # We do not want to remove unused products other than our own

# echo "Deleting unused products"
# $PCF delete-unused-products
# echo

# echo "Available products:"
# $PCF products
# echo

# if $PCF is-available "${PRODUCT}" ; then
# 	echo "${PRODUCT} remains available - remove failed"
# 	exit 1
# fi
