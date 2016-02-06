#!/bin/sh -e

TILE_DIR="$( cd "$1" && pwd )"
POOL_DIR="$( cd "$2" && pwd )"

MY_DIR="$( cd "$( dirname "$0" )" && pwd )"
REPO_DIR="$( cd "${MY_DIR}/../.." && pwd )"
BASE_DIR="$( cd "${REPO_DIR}/.." && pwd )"
TEST_DIR="$( cd "${REPO_DIR}/ci/deployment-tests" && pwd )"

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
python "${TEST_DIR}/pcf" products
echo

echo "Uninstalling ${PRODUCT}"
python "${TEST_DIR}/pcf" uninstall "${PRODUCT}"
echo

echo "Applying Changes"
python "${TEST_DIR}/pcf" apply-changes
echo

echo "Available products:"
python "${TEST_DIR}/pcf" products
echo

if python "${TEST_DIR}/pcf" is-installed "${PRODUCT}" ; then
	echo "${PRODUCT} remains installed - remove failed"
	exit 1
fi

exit 0 # We do not want to remove unused products other than our own

# echo "Deleting unused products"
# python "${TEST_DIR}/pcf" delete-unused-products
# echo

# echo "Available products:"
# python "${TEST_DIR}/pcf" products
# echo

# if python "${TEST_DIR}/pcf" is-available "${PRODUCT}" ; then
# 	echo "${PRODUCT} remains available - remove failed"
# 	exit 1
# fi
