#!/usr/bin/env bash

set -ex

echo "Be sure to increment version if re-using an environment"
version=0.1.2

rm -rf dev_releases/no-op-release
bosh create-release --force --version=$version --tarball=../resources/no-op-release.tgz
