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

from __future__ import absolute_import, division, print_function, unicode_literals
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

def build(config, verbose=False):
	validate_config(config)
	context = config.copy()
	add_defaults(context)
	upgrade_config(context)
	context['verbose'] = verbose
	releases = BoshReleases(context)
	with cd('release', clobber=True):
		packages = context.get('packages', [])
		for package in packages:
			releases.add_package(package)
	validate_memory_quota(context)
	with cd('product', clobber=True):
		releases.create_tile()

def validate_config(config):
	try:
		validname = re.compile('[a-z][a-z0-9]+(-[a-z0-9]+)*$')
		if validname.match(config['name']) is None:
			print('product name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens', file=sys.stderr)
			sys.exit(1)
	except KeyError as e:
		print('tile.yml is missing mandatory property', e, file=sys.stderr)
		sys.exit(1)
	for package in config.get('packages', []):
		try:
			if validname.match(package['name']) is None:
				print('package name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens', file=sys.stderr)
				sys.exit(1)
		except KeyError as e:
			print('package is missing mandatory property', e, file=sys.stderr)
			sys.exit(1)
	return config

def upgrade_config(config):
	# v0.9 specified auto_services as a space-separated string of service names
	for package in config.get('packages', []):
		auto_services = package.get('auto_services', None)
		if auto_services is not None:
			if isinstance(auto_services, str):
				package['auto_services'] = [ { 'name': s } for s in auto_services.split()]
	# v0.9 expected a string manifest for docker-bosh releases
	for package in config.get('packages', []):
		if package.get('type') == 'docker-bosh':
			manifest = package.get('manifest')
			if manifest is not None and isinstance(manifest, str):
				package['manifest'] = yaml.safe_load(manifest)

def add_defaults(context):
	context['stemcell_criteria'] = default_stemcell(context)
	context['all_properties'] = context.get('properties', [])
	context['total_memory'] = 0
	context['max_memory'] = 0
	for form in context.get('forms', []):
		properties = form.get('properties', [])
		for property in properties:
			if 'configurable' not in property:
				property['configurable'] = True
		context['all_properties'] += properties
	for property in context['all_properties']:
		property['name'] = property['name'].lower().replace('-','_')
		default = property.get('default', property.pop('value', None)) # NOTE this intentionally removes property['value']
		if default is not None:
			property['default'] = default
		property['configurable'] = property.get('configurable', False)
		property['optional'] = property.get('optional', False)

def default_stemcell(context):
	stemcell_criteria = context.get('stemcell_criteria', {})
	stemcell_criteria['os'] = stemcell_criteria.get('os', 'ubuntu-trusty')
	stemcell_criteria['version'] = stemcell_criteria.get('version', latest_stemcell(stemcell_criteria['os']))
	print('stemcell_criteria:')
	print('  os:', stemcell_criteria['os'])
	print('  version:', stemcell_criteria['version'])
	print()
	return stemcell_criteria

def latest_stemcell(os):
	if os == 'ubuntu-trusty':
		headers = { 'Accept': 'application/json' }
		response = requests.get('https://network.pivotal.io/api/v2/products/stemcells/releases', headers=headers)
		response.raise_for_status()
		releases = response.json()['releases']
		versions = [r['version'] for r in releases]
		latest_major = sorted(versions)[-1].split('.')[0]
		return latest_major
	return None # TODO - Look for latest on bosh.io for given os

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
