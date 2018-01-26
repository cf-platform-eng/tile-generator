#!/usr/bin/env bash

set -ex

echo "Be sure to increment version if re-using an environment"
version=0.1.2

rm -rf dev_releases/runtime-test-release
bosh create-release --force --version=$version --tarball=../resources/runtime-test-release.tgz
