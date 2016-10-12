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

# The Config object describes exactly what the Tile Generator is going to generate.
# It starts with a minimal configuration passed in as keyword arguments or read
# from tile.yml, then is gradually transformed into a complete configuration
# through the following phases:
#
# Validate - ensure that all mandatory fields are present, and that any values
# provided meet the constraints for that specific property
#
# Add Defaults - Completes the configuration by inserting defaults for any properties
# not specified in tile.yml. Doing this here allows the remainder of the code to
# safely assume presence of properties (i.e. use config['property'])
#
# Upgrade - Maintains backward compatibility for deprecated tile.yml syntax by
# translating it into currently supported syntax. Doing so here allows us to only
# handle new syntax in the rest of the code, while still maintaining backward
# compatibility
#
# Process Packages - Normalizes all package desctiptions and sorts them into the
# appropriate bosh releases depending on their types

# TODO - Remove jobs and requires flags (after rest of code is made independent of it)

package_types = {
	'app':               { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_app' ] },
	'app-broker':        { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app' ] },
	'external-broker':   { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_broker', 'is_external_broker' ] },
	'buildpack':         { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_buildpack' ] },
	'docker-bosh':       { 'flags': [ 'requires_docker_bosh', 'is_docker_bosh', 'is_docker' ], 'jobs':  [ 'docker-bosh' ] },
	'docker-app':        { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_app', 'is_docker_app', 'is_docker' ] },
	'docker-app-broker': { 'flags': [ 'is_cf', 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app', 'is_docker_app', 'is_docker' ] },
	'blob':              { 'flags': [ 'is_cf', 'is_blob' ] },
	'bosh-release':      { 'flags': [ 'is_bosh_release' ] },
}

class Config(dict):

	def __init__(self, *arg, **kw):
		super(Config, self).__init__(*arg, **kw)

	def read(self):
		self.read_config()
		self.read_history()
		self.transform()
		return self

	def transform(self):
		self.validate()
		self.add_defaults()
		self.upgrade()
		self.process_packages()

	def process_packages(self):
		for package in self.get('packages', []):
			name = package['name']
			typename = package['type']
			typedef = package_types[typename]
			flags = typedef.get('flags', [])
			jobs = typedef.get('jobs', [])
			for flag in flags:
				package[flag] = True
			release = self.release_for_package(package)
			release['packages'][name] = package
			# TODO - Remove original package definition (after rest of code is made independent of it)

	def release_for_package(self, package):
		release_name = self['name'] if package.get('is_cf', False) else package['name']
		release = self['releases'].get(release_name, None)
		if release is None:
			release = { 'name': release_name, 'packages': {}, 'jobs': {} }
			if package.get('is_cf', False):
				release['jobs']['deploy-all'] = { 'name': 'deploy-all' }
				release['jobs']['delete-all'] = { 'name': 'delete-all' }
				release['requires_cf_cli'] = True
			if package.get('is_docker_bosh', False):
				release['jobs']['docker-bosh'] = { 'name': 'docker-bosh', 'package': package }
				release['requires_docker_bosh'] = True
			self['releases'][release_name] = release
		release['packages'] = release.get('packages', {})
		release['jobs'] = release.get('jobs', {})
		return release

	def save_history(self):
		with open(HISTORY_FILE, 'wb') as history_file:
			write_yaml(history_file, self['history'])

	def validate(self):
		try:
			validname = re.compile('[a-z][a-z0-9]*(-[a-z0-9]+)*$')
			if validname.match(self['name']) is None:
				print('product name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens', file=sys.stderr)
				sys.exit(1)
		except KeyError as e:
			print('tile.yml is missing mandatory property', e, file=sys.stderr)
			sys.exit(1)
		for package in self.get('packages', []):
			try:
				if validname.match(package['name']) is None:
					print('package name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens', file=sys.stderr)
					sys.exit(1)
				if package['type'] not in package_types:
					print('package', package['name'], 'has invalid type', package['type'], file=sys.stderr)
					print('valid types are:', ', '.join([ t for t in package_types]), file=sys.stderr)
					sys.exit(1)
			except KeyError as e:
				if str(e) == '\'name\'':
					print('package is missing mandatory property', e, file=sys.stderr)
				else:
					print('package', package['name'], 'is missing mandatory property', e, file=sys.stderr)
				sys.exit(1)

	def set_verbose(self, verbose=True):
		self['verbose'] = verbose

	def set_docker_cache(self, docker_cache=None):
		if docker_cache is not None:
			self['docker_cache'] = docker_cache

	def add_defaults(self):
		self['stemcell_criteria'] = self.default_stemcell()
		self['all_properties'] = self.get('properties', [])
		self['total_memory'] = 0
		self['max_memory'] = 0
		self['releases'] = self.get('releases', {})
		for form in self.get('forms', []):
			properties = form.get('properties', [])
			for property in properties:
				if 'configurable' not in property:
					property['configurable'] = True
			self['all_properties'] += properties
		for property in self['all_properties']:
			property['name'] = property['name'].lower().replace('-','_')
			default = property.get('default', property.pop('value', None)) # NOTE this intentionally removes property['value']
			if default is not None:
				property['default'] = default
			property['configurable'] = property.get('configurable', False)
			property['optional'] = property.get('optional', False)

	def default_stemcell(self):
		stemcell_criteria = self.get('stemcell_criteria', {})
		stemcell_criteria['os'] = stemcell_criteria.get('os', 'ubuntu-trusty')
		stemcell_criteria['version'] = stemcell_criteria.get('version', self.latest_stemcell(stemcell_criteria['os']))
		return stemcell_criteria

	def latest_stemcell(self, os):
		if os == 'ubuntu-trusty':
			headers = { 'Accept': 'application/json' }
			response = requests.get('https://network.pivotal.io/api/v2/products/stemcells/releases', headers=headers)
			response.raise_for_status()
			releases = response.json()['releases']
			versions = [r['version'] for r in releases]
			latest_major = sorted(versions)[-1].split('.')[0]
			return latest_major
		return None # TODO - Look for latest on bosh.io for given os

	def upgrade(self):
		# v0.9 specified auto_services as a space-separated string of service names
		for package in self.get('packages', []):
			auto_services = package.get('auto_services', None)
			if auto_services is not None:
				if isinstance(auto_services, str):
					package['auto_services'] = [ { 'name': s } for s in auto_services.split()]
		# v0.9 expected a string manifest for docker-bosh releases
		for package in self.get('packages', []):
			if package.get('type') == 'docker-bosh':
				manifest = package.get('manifest')
				if manifest is not None and isinstance(manifest, str):
					package['manifest'] = yaml.safe_load(manifest)

	def read_config(self):
		try:
			with open(CONFIG_FILE) as config_file:
				self.update(read_yaml(config_file))
		except IOError as e:
			print('Not a tile repository. Use "tile init" in the root of your repository to create one.', file=sys.stderr)
			sys.exit(1)

	def read_history(self):
		try:
			with open(HISTORY_FILE) as history_file:
				self['history'] = read_yaml(history_file)
		except IOError as e:
			self['history'] = {}

	def set_version(self, version):
		if version is None:
			version = 'patch'
		history = self.get('history', {})
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
		self['version'] = version

def read_yaml(file):
	return yaml.safe_load(file)

def write_yaml(file, data):
	file.write(yaml.safe_dump(data, default_flow_style=False, explicit_start=True))

def is_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+([\\-+][0-9a-zA-Z]+(\\.[0-9a-zA-Z]+)*)*$')
	return valid.match(version) is not None

def is_unannotated_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+$')
	return valid.match(version) is not None
