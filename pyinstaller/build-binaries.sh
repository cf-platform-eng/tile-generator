#!/bin/bash

# tile-generator
#
# Copyright (c) 2015-Present Pivotal Software, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
VENV="$SCRIPT_DIR/build-env"

function show_help {
  echo "Usage: `basename "$0"` [OPTIONS]

Options:
  --help  Show this message and exit.
  --recreate-venv Recreate the virtual environment and start from scratch.
  --statix Use staticx to ship a fully static package.
"
}

function create_venv {
  deactivate >/dev/null 2>&1 || echo ''
  rm -rf $VENV
  echo "Creating a new virtual environment..."
  virtualenv -q -p python3 $VENV
  source $VENV/bin/activate
  # Build for current project. Assumes tile-generator src is up a dir
  pip install -e $SCRIPT_DIR/../
  #https://github.com/pypa/pip/issues/6163#issuecomment-456772043
  pip install pyinstaller --no-use-pep517
  pip install staticx
}

function create_binaries {
  source $VENV/bin/activate
  pyinstaller -y $SCRIPT_DIR/pcf.spec
  pyinstaller -y $SCRIPT_DIR/tile.spec
}

function statix_all {
  create_binaries
  staticx dist/tile* dist/tile*
  staticx dist/pcf* dist/pcf*
}

if [ ! -d $VENV ]; then
  create_venv
fi

if [ ! -n "$1" ]; then
  # No options passed. Do the build.
  create_binaries
fi

while [ -n "$1" ]; do
  case "$1" in
    -h) show_help ;;
    --help) show_help ;;
    --recreate-venv) create_venv ;;
    --staticx) statix_all ;;
    *) echo "Option not recognized '$1'"; show_help ;;
  esac
  shift
done

