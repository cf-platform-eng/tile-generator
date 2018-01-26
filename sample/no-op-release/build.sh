#!/usr/bin/env bash

set -ex

echo "Be sure to increment version if re-using an environment"
version=0.1.3

rm -rf dev_releases/no-op-release

# pcf-1-11 didn't like the bosh release build with bosh2
# bosh2 version
#bosh create-release --force --version=$version --tarball=../resources/no-op-release.tgz

# bosh1 version
bosh create release --force --version=$version --with-tarball
mv dev_releases/no-op-release/no-op-release-0.1.3.tgz ../resources/no-op-release.tgz
