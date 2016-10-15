#!/usr/bin/env python

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

from __future__ import absolute_import, division, print_function
import os
import sys
import errno
import requests
import shutil
import subprocess
import tarfile
from . import template
try:
	# Python 3
	from urllib.request import urlretrieve
except ImportError:
	# Python 2
	from urllib import urlretrieve
import zipfile
import yaml
import datetime

from .bosh import *
from .util import *

LIB_PATH = os.path.dirname(os.path.realpath(__file__))
REPO_PATH = os.path.realpath(os.path.join(LIB_PATH, '..'))
DOCKER_BOSHRELEASE_VERSION = '23'

def build(config):
	releases = BoshReleases(config)
	bosh_releases = {}
	with cd('release', clobber=True):
		for release in config.get('releases', []):
			release_name = release['name']
			bosh_release = BoshRelease(release_name, config)
			bosh_releases[release_name] = bosh_release
			for package in release.get('packages', []):
				releases.add_package(bosh_release, package)
	with cd('product', clobber=True):
		releases.create_tile(bosh_releases)
