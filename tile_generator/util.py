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
import errno
import os
import requests
import shutil
import sys
try:
	# Python 3
	from urllib.request import urlretrieve
except ImportError:
	# Python 2
	from urllib import urlretrieve

# FIXME this wants to be a dict with 'typename' as the key.
package_types = [
	# A + at the start of the job type indicates it is a post-deploy errand
	# A - at the start of the job type indicates it is a pre-delete errand
	{
		'typename': 'app',
		'flags': [ 'requires_cf_cli', 'is_app' ],
	},
	{
		'typename': 'app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app' ],
	},
	{
		'typename': 'external-broker',
		'flags': [ 'requires_cf_cli', 'is_broker', 'is_external_broker' ],
	},
	{
		'typename': 'buildpack',
		'flags': [ 'requires_cf_cli', 'is_buildpack' ],
	},
	{
		'typename': 'docker-bosh',
		'flags': [ 'requires_docker_bosh', 'is_docker_bosh', 'is_docker' ],
		'jobs':  [ 'docker-bosh' ],
	},
	{
		'typename': 'docker-app',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_docker_app', 'is_docker' ],
	},
	{
		'typename': 'docker-app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app', 'is_docker_app', 'is_docker' ],
	},
	{
		'typename': 'blob',
		'flags': [ 'is_blob' ],
	},
	{
		'typename': 'bosh-release',
		'flags': [ 'is_bosh_release' ],
	}
]

def download_docker_image(docker_image, target_file, cache=None):
	try:
		from docker.client import Client
		from docker.utils import kwargs_from_env
		kwargs = kwargs_from_env()
		kwargs['tls'] = False
		docker_cli = Client(**kwargs)
		image = docker_cli.get_image(docker_image)
		image_tar = open(target_file,'w')
		image_tar.write(image.data)
		image_tar.close()
	except Exception as e:
		if cache is not None:
			cached_file = os.path.join(cache, docker_image.lower().replace('/','-').replace(':','-') + '.tgz')
			if os.path.isfile(cached_file):
				print('using cached version of', docker_image)
				urlretrieve(cached_file, target_file)
				return
			print(docker_image, 'not found in cache', cache, file=sys.stderr)
			sys.exit(1)
		if isinstance(e, KeyError):
			print('docker not configured on this machine (or environment variables are not properly set)', file=sys.stderr)
		else:
			print(docker_image, 'not found on local machine', file=sys.stderr)
			print('you must either pull the image, or download it and use the --docker-cache option', file=sys.stderr)
		sys.exit(1)


def bosh_extract(output, properties):
	result = {}
	for l in output.split('\n'):
		for p in properties:
			if l.startswith(p['pattern']):
				result[p['label']] = l.split(':', 1)[-1].strip()
	return result

class cd:
	"""Context manager for changing the current working directory"""
	def __init__(self, newPath, clobber=False):
		self.clobber = clobber
		self.newPath = os.path.expanduser(newPath)

	def __enter__(self):
		self.savedPath = os.getcwd()
		if self.clobber and os.path.isdir(self.newPath):
			shutil.rmtree(self.newPath)
		mkdir_p(self.newPath)
		os.chdir(self.newPath)

	def __exit__(self, etype, value, traceback):
		os.chdir(self.savedPath)

def mkdir_p(dir):
	try:
		os.makedirs(dir)
	except os.error as e:
		if e.errno != errno.EEXIST:
			raise

def download(url, filename):
	# [mboldt:20160908] Using urllib.urlretrieve gave an "Access
	# Denied" page when trying to download docker boshrelease.
	# I don't know why. requests.get works. Do what works.
	# urllib.urlretrieve(url, filename)
	response = requests.get(url, stream=True)
	response.raise_for_status()
	with open(filename, 'wb') as file:
		for chunk in response.iter_content(chunk_size=1024):
			if chunk:
				file.write(chunk)

def update_memory(context, manifest):
	memory = manifest.get('memory', '1G')
	unit = memory.lstrip('0123456789').lstrip(' ').lower()
	if unit not in [ 'g', 'gb', 'm', 'mb' ]:
		print('invalid memory size unit', unit, 'in', memory, file=sys.stderr)
		sys.exit(1)
	memory = int(memory[:-len(unit)])
	if unit in [ 'g', 'gb' ]:
		memory *= 1024
	context['total_memory'] += memory
	if memory > context['max_memory']:
		context['max_memory'] = memory
