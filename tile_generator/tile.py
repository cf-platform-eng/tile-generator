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
import yaml
import os
import types
from . import build
from . import template
from . import config
from .config import Config
from.version import version_string

@click.group()
@click.version_option(version_string, '-v', '--version', message='%(prog)s version %(version)s')
def cli():
	pass

@cli.command('init')
@click.argument('name', nargs=1, required=False)
def init_cmd(name):
	dir = '.'
	if name is not None:
		dir = name
		os.mkdir(name)
		os.chdir(name)
	if os.path.isfile(config.CONFIG_FILE):
		print('Already initialized.', file=sys.stderr)
		sys.exit(0)
	name = os.path.basename(os.getcwd())
	template.render(config.CONFIG_FILE, config.CONFIG_FILE, { 'name': name })
	template.render('.gitignore', 'gitignore', {})
	print('Generated initial tile files; begin by customizing "{}/tile.yml"'.format(dir))

@cli.command('build')
@click.argument('version', required=False)
@click.option('--verbose', is_flag=True)
@click.option('--sha1', is_flag=True)
@click.option('--cache', type=str, default=None)
def build_cmd(version, verbose, sha1, cache):
	cfg = Config().read()

	cfg.set_version(version)
	cfg.set_verbose(verbose)
	cfg.set_sha1(sha1)
	cfg.set_cache(cache)
	print('name:', cfg.get('name', '<unspecified>'))
	print('label:', cfg.get('label', '<unspecified>'))
	print('description:', cfg.get('description', '<unspecified>'))
	print('version:', cfg.get('version', '<unspecified>'))
	print('sha1:', cfg.get('sha1', '<unspecified>'))
	stemcell = cfg.get('stemcell_criteria', {})
	print('stemcell:', stemcell.get('os', '<unspecified>'), stemcell.get('version', '<unspecified>'))
	print()
	build.build(cfg)
	cfg.save_history()

@cli.command('expand')
@click.argument('version', required=False)
def expand_cmd(version):
	cfg = Config().read()
	cfg.set_version(version)
	config.write_yaml(sys.stdout, dict(cfg))

def main():
  try:
    cli(prog_name='tile')
  except Exception as e:
    click.echo(e, err=True)
    sys.exit(1)


if __name__ == '__main__':
  main()