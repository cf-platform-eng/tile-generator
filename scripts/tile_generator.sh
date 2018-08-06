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
VENV="$SCRIPT_DIR/tile-generator-env"

function show_help {
  echo "Usage: `basename "$0"` [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.
  --clear Clear out the virtual environment and start from scratch. 

Commands:
  tile
  pcf
"
}

function create_venv {
  deactivate >/dev/null 2>&1 || echo ''
  rm -rf $VENV
  echo "Creating a new virtual environment..."
  virtualenv -q -p python2 $VENV
  source $VENV/bin/activate
  pip install tile-generator
  source $VENV/bin/activate
}

if [ ! -d $VENV ]; then
  create_venv
fi

if [ ! -n "$1" ]; then
  show_help
fi

while [ -n "$1" ]; do
  case "$1" in
    -h) show_help ;;
    --help) show_help ;;
    --clear) create_venv ;;
    tile) shift; source $VENV/bin/activate; tile "$@"; break ;;
    pcf) shift; source $VENV/bin/activate; pcf "$@"; break ;;
    *) echo "Command or option not recognized '$1'"; show_help ;;
  esac
  shift
done

