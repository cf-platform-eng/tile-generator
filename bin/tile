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

import click
import sys
import os
import yaml

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(PATH, os.path.join('..', 'lib')))
import build
import template

CONFIG_FILE = "tile.yml"
HISTORY_FILE = "tile-history.yml"

@click.group()
def cli():
	pass

@cli.command('init')
@click.argument('name', nargs=1, required=False)
def init_cmd(name):
	if name is not None:
		os.mkdir(name)
		os.chdir(name)
	if os.path.isfile(CONFIG_FILE):
		print >>sys.stderr, 'Already initialized.'
		sys.exit(0)
	name = os.path.basename(os.getcwd())
	template.render(CONFIG_FILE, CONFIG_FILE, { 'name': name })

@cli.command('build')
@click.argument('version', 'patch', required=False)
@click.option('--verbose', is_flag=True)
@click.option('--docker-cache', type=str, default=None)
def build_cmd(version, verbose, docker_cache):
	config = read_config()
	history = read_history()
	config['history'] = history
	config['version'] = build.update_version(history, version)
	if docker_cache is not None:
		config['docker_cache'] = docker_cache
	print 'name:', config.get('name', '<unspecified>')
	print 'icon:', config.get('icon_file', '<unspecified>')
	print 'label:', config.get('label', '<unspecified>')
	print 'description:', config.get('description', '<unspecified>')
	print 'version:', config.get('version', '<unspecified>')
	print
	build.build(config, verbose)
	write_history(history)

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

def write_history(history):
	with open(HISTORY_FILE, 'wb') as history_file:
		write_yaml(history_file, history)

def read_yaml(file):
	return yaml.safe_load(file)

def write_yaml(file, data):
	file.write('---\n')
	file.write(yaml.safe_dump(data, default_flow_style=False))

if __name__ == "__main__":
	cli()
