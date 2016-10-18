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
	build_bosh_releases(config)
	build_tile(config)

def build_bosh_releases(config):
	mkdir_p('release', clobber=True)
	for release in config.get('releases', []):
		release_name = release['name']
		bosh_release = BoshRelease(release, config)
		release.update(bosh_release.pre_create_tile())

def build_tile(context):
	mkdir_p('product', clobber=True)
	context['release'] = context.get('releases')[0]
	tile_name = context['name']
	tile_version = context['version']
	mkdir_p('product/releases')
	# FIXME Don't treat the docker bosh release specially; just add it as another BoshRelease.
	if context['requires_docker_bosh']:
		print('tile import release docker')
		docker_release = download_docker_release(version=context.get('docker_bosh_version', None), cache=context.get('cache', None))
		context['docker_release'] = docker_release
	print('tile generate metadata')
	template.render('product/metadata/' + tile_name + '.yml', 'tile/metadata.yml', context)
	print('tile generate content-migrations')
	template.render('product/content_migrations/' + tile_name + '.yml', 'tile/content-migrations.yml', context)
	print('tile generate migrations')
	migrations = 'product/migrations/v1/' + datetime.datetime.now().strftime('%Y%m%d%H%M') + '_noop.js'
	template.render(migrations, 'tile/migration.js', context)
	print('tile generate package')
	pivotal_file = os.path.join('product', tile_name + '-' + tile_version + '.pivotal')
	with zipfile.ZipFile(pivotal_file, 'w') as f:
		if context['requires_docker_bosh']:
			docker_release = context['docker_release']
			f.write(
				os.path.join('product/releases', docker_release['file']),
				os.path.join('releases', docker_release['file']))
		for release in context.get('releases', []):
			print('tile import release', release['name'])
			shutil.copy(release['tarball'], os.path.join('product/releases', release['file']))
			f.write(
				os.path.join('product/releases', release['file']),
				os.path.join('releases', release['file']))
		f.write(
			os.path.join('product/metadata', tile_name + '.yml'),
			os.path.join('metadata', tile_name + '.yml'))
		f.write(
			os.path.join('product/content_migrations', tile_name + '.yml'),
			os.path.join('content_migrations', tile_name + '.yml'))
		f.write(migrations, migrations.lstrip('product/'))
	print()
	print('created tile', pivotal_file)
