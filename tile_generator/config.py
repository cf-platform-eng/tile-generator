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

from __future__ import absolute_import, division, print_function#, unicode_literals
import sys
import yaml
import re
import requests

CONFIG_FILE = "tile.yml"
HISTORY_FILE = "tile-history.yml"

def get(version=None, docker_cache=None):
	config = read_config()
	config = validate_config(config)
	add_defaults(config)
	upgrade_config(config)
	history = read_history()
	config['history'] = history
	config['version'] = update_version(history, version)
	if docker_cache is not None:
		config['docker_cache'] = docker_cache
	return config

def commit(config):
	with open(HISTORY_FILE, 'wb') as history_file:
		write_yaml(history_file, config['history'])

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

def read_config():
	try:
		with open(CONFIG_FILE) as config_file:
			return read_yaml(config_file)
	except IOError as e:
		print('Not a tile repository. Use "tile init" in the root of your repository to create one.', file=sys.stderr)
		sys.exit(1)

def read_history():
	try:
		with open(HISTORY_FILE) as history_file:
			return read_yaml(history_file)
	except IOError as e:
		return {}

def read_yaml(file):
	return yaml.safe_load(file)

def write_yaml(file, data):
	file.write('---\n')
	file.write(yaml.safe_dump(data, default_flow_style=False))

def update_version(history, version):
	if version is None:
		version = 'patch'
	prior_version = history.get('version', None)
	if prior_version is not None:
		history['history'] = history.get('history', [])
		history['history'] += [ prior_version ]
	if not is_semver(version):
		semver = history.get('version', '0.0.0')
		if not is_unannotated_semver(semver):
			print('The prior version was', semver, file=sys.stderr)
			print('To auto-increment, the prior version must be in semver format (x.y.z), and must not include a label.', file=sys.stderr)
			sys.exit(1)
		semver = semver.split('.')
		if version == 'patch':
			semver[2] = str(int(semver[2]) + 1)
		elif version == 'minor':
			semver[1] = str(int(semver[1]) + 1)
			semver[2] = '0'
		elif version == 'major':
			semver[0] = str(int(semver[0]) + 1)
			semver[1] = '0'
			semver[2] = '0'
		else:
			print('Argument must specify "patch", "minor", "major", or a valid semver version (x.y.z)', file=sys.stderr)
			sys.exit(1)
		version = '.'.join(semver)
	history['version'] = version
	return version

def is_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+([\\-+][0-9a-zA-Z]+(\\.[0-9a-zA-Z]+)*)*$')
	return valid.match(version) is not None

def is_unannotated_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+$')
	return valid.match(version) is not None
