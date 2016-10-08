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

import sys
import yaml
import re

CONFIG_FILE = "tile.yml"
HISTORY_FILE = "tile-history.yml"

def get(version=None, docker_cache=None):
	config  = read_config()
	history = read_history()
	config['history'] = history
	config['version'] = update_version(history, version)
	if docker_cache is not None:
		config['docker_cache'] = docker_cache
	return config

def commit(config):
	with open(HISTORY_FILE, 'wb') as history_file:
		write_yaml(history_file, config['history'])

def read_config():
	try:
		with open(CONFIG_FILE) as config_file:
			return read_yaml(config_file)
	except IOError as e:
		print >> sys.stderr, 'Not a tile repository. Use "tile init" in the root of your repository to create one.'
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
			print >>sys.stderr, 'The prior version was', semver
			print >>sys.stderr, 'To auto-increment, the prior version must be in semver format (x.y.z), and must not include a label.'
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
			print >>sys.stderr, 'Argument must specify "patch", "minor", "major", or a valid semver version (x.y.z)'
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
