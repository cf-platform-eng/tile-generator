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
	with cd('release', clobber=True):
		packages = config.get('packages', [])
		for package in packages:
			releases.add_package(package)
	validate_memory_quota(config)
	with cd('product', clobber=True):
		releases.create_tile()

def validate_memory_quota(context):
	required = context['total_memory'] + context['max_memory']
	specified = context.get('org_quota', None)
	if specified is None:
		# We default to twice the total size
		# For most cases this is generous, but there's no harm in it
		context['org_quota'] = context['total_memory'] * 2
	elif specified < required:
		print('Specified org quota of', specified, 'MB is insufficient', file=sys.stderr)
		print('Required quota is at least the total package size of', context['total_memory'], 'MB', file=sys.stderr)
		print('Plus enough room for blue/green deployment of the largest app:', context['max_memory'], 'MB', file=sys.stderr)
		print('For a total of:', required, 'MB', file=sys.stderr)
		sys.exit(1)
