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
	bosh_releases = {}
	mkdir_p('release', clobber=True)
	for release in config.get('releases', []):
		release_name = release['name']
		bosh_release = BoshRelease(release, config)
		bosh_releases[release_name] = bosh_release
	mkdir_p('product', clobber=True)
	create_tile(config, bosh_releases)

def create_tile(context, releases):
	release_info = {}
	for name, release in releases.items():
		release_info.update(release.pre_create_tile())
	if 'tarball' in release_info:
		release_info['file'] = os.path.basename(release_info['tarball'])
	context['release'] = release_info
	# Can we just compute release_info instead of parsing from bosh in pre_create_tile?
	release_name = release_info.get('name', context.get('name', None))
	release_version = release_info.get('version', context.get('version', None))
	mkdir_p('product/releases')
	# FIXME Don't treat the docker bosh release specially; just add it as another BoshRelease.
	if context['requires_docker_bosh']:
		print('tile import release docker')
		docker_release = download_docker_release(version=context.get('docker_bosh_version', None), cache=context.get('cache', None))
		context['docker_release'] = docker_release
	print('tile generate metadata')
	template.render('product/metadata/' + release_name + '.yml', 'tile/metadata.yml', context)
	print('tile generate content-migrations')
	template.render('product/content_migrations/' + release_name + '.yml', 'tile/content-migrations.yml', context)
	print('tile generate migrations')
	migrations = 'product/migrations/v1/' + datetime.datetime.now().strftime('%Y%m%d%H%M') + '_noop.js'
	template.render(migrations, 'tile/migration.js', context)
	print('tile generate package')
	pivotal_file = os.path.join('product', release_name + '-' + release_version + '.pivotal')
	with zipfile.ZipFile(pivotal_file, 'w') as f:
		if context['requires_docker_bosh']:
			docker_release = context['docker_release']
			f.write(
				os.path.join('product/releases', docker_release['file']),
				os.path.join('releases', docker_release['file']))
		for name, release in releases.items():
			print('tile import release', name)
			shutil.copy(release.tarball, os.path.join('product/releases', release.file))
			f.write(
				os.path.join('product/releases', release.file),
				os.path.join('releases', release.file))
		f.write(
			os.path.join('product/metadata', release_name + '.yml'),
			os.path.join('metadata', release_name + '.yml'))
		f.write(
			os.path.join('product/content_migrations', release_name + '.yml'),
			os.path.join('content_migrations', release_name + '.yml'))
		f.write(migrations, migrations.lstrip('product/'))
	print()
	print('created tile', pivotal_file)
