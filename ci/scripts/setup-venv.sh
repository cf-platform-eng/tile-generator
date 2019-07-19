#!/bin/sh -e

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

_VENV="/tmp/tile-generator-env"

if [ -z "${REPO_DIR}" ]; then
  echo "REPO_DIR env variable is not set. Needs to point to tile-generator repo dir."
  exit 1
fi

deactivate >/dev/null 2>&1 || echo ''

# If there is no venv dir or anything passed to this script
if [ ! -d "${_VENV}" ] || [ "$1" = "recreate" ]; then
  rm -rf "${_VENV}"
  echo "Creating a new virtual environment..."
  virtualenv -p python3 "${_VENV}"
  . "${_VENV}/bin/activate"
  cd "${REPO_DIR}"
  pwd
  pip install -e .
  echo 'sdf'
else
  echo "Using virtual environment located at ${_VENV}..." 
fi

. "$_VENV/bin/activate"
command -v tile >/dev/null 2>&1 || { echo "Command 'tile' not found. Virtualenv at ${_VENV} must be corrupt." >&2; exit 1; }
