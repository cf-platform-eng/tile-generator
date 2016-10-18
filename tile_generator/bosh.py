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
import re
import datetime

from .util import *

def read_release_manifest(bosh_release_tarball):
	with tarfile.open(bosh_release_tarball) as tar:
		manifest_file = tar.extractfile('./release.MF')
		manifest = yaml.safe_load(manifest_file)
		manifest_file.close()
		return manifest

# FIXME we shouldn't treat the docker bosh release specially.
def download_docker_release(version=None, cache=None):
	version_param = '?v=' + version if version else ''
	url = 'https://bosh.io/d/github.com/cf-platform-eng/docker-boshrelease' + version_param
	localfile = 'product/releases/docker-boshrelease.tgz'
	download(url, localfile, cache)
	manifest = read_release_manifest(localfile)
	print("Downloaded docker version", manifest['version'], file=sys.stderr)
	return {
		'tarball': localfile,
		'name': manifest['name'],
		'version': manifest['version'],
		'file': os.path.basename(localfile),
	}

class BoshRelease:

	def __init__(self, release, context):
		self.name = release['name']
		# TODO - To allow for multiple bosh releases to be built
		# self.release_dir = os.path.join('release', self.name)
		self.release_dir = 'release'
		self.jobs = release.get('jobs', [])
		self.packages = release.get('packages', [])
		self.context = context
		self.config = release

	# Build the bosh release, if needed.
	def pre_create_tile(self):
		if self.config.get('is_bosh_release', False):
			print("bosh release", self.name, "already built")
			self.tarball = os.path.realpath(self.config['path'])
			self.file = os.path.basename(self.tarball)
			manifest = read_release_manifest(self.tarball)
			self.name = manifest['name']
			self.version = manifest['version']
			release_info = {
				'release_name': self.name,
				'version': self.version,
				'file': self.file,
				'tarball': self.tarball,
			}
			self.context['bosh_releases'] = self.context.get('bosh_releases', []) + [ release_info ]
			return release_info
		print("bosh release", self.name, "needs to be built")
		mkdir_p(self.release_dir)
		self.__bosh('init', 'release')
		template.render(
			os.path.join(self.release_dir, 'config/final.yml'),
			'config/final.yml',
			self.context)
		for package in self.packages:
			self.add_blob_package(package)
		for job in self.jobs:
			self.add_bosh_job(
				job.get('package', None),
				job['name'].lstrip('+-'),
				post_deploy=job['name'].startswith('+'),
				pre_delete=job['name'].startswith('-')
			)
		if self.config.get('requires_cf_cli', False):
			self.add_cf_cli()
		self.add_common_utils()
		self.__bosh('upload', 'blobs')
		output = self.__bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', self.context['version'])
		release_info = bosh_extract(output, [
			{ 'label': 'release_name', 'pattern': 'Release name' },
			{ 'label': 'version', 'pattern': 'Release version' },
			{ 'label': 'manifest', 'pattern': 'Release manifest' },
			{ 'label': 'tarball', 'pattern': 'Release tarball' },
		])
		self.tarball = release_info['tarball']
		self.file = os.path.basename(self.tarball)
		release_info['file'] = self.file
		return release_info

	def add_cf_cli(self):
		self.add_blob_package(
			{
				'name': 'cf_cli',
				'files': [{
					'name': 'cf-linux-amd64.tgz',
					'path': 'http://cli.run.pivotal.io/stable?release=linux64-binary&source=github-rel'
				},{
					'name': 'all_open.json',
					'path': template.path('src/templates/all_open.json')
				}]
			},
			alternate_template='cf_cli'
		)
		self.context['requires_product_versions'] = self.context.get('requires_product_versions', []) + [
			{
				'name': 'cf',
				'version': '~> 1.5'
			}
		]

	def add_common_utils(self):
		self.add_src_package(
		{
			'name': 'common',
			'files': [{
				'name': 'utils.sh',
				'path': template.path('src/common/utils.sh')
			}]
		},
		alternate_template='common'
	)

	def add_bosh_job(self, package, job_type, post_deploy=False, pre_delete=False):
		is_errand = post_deploy or pre_delete
		job_name = job_type
		if package is not None:
			job_name += '-' + package['name']

		self.__bosh('generate', 'job', job_name)
		job_context = {
			'job_name': job_name,
			'job_type': job_type,
			'context': self.context,
			'package': package,
			'errand': is_errand,
		}
		template.render(
			os.path.join(self.release_dir, 'jobs', job_name, 'spec'),
			os.path.join('jobs', 'spec'),
			job_context
		)
		template.render(
			os.path.join(self.release_dir, 'jobs', job_name, 'templates', job_name + '.sh.erb'),
			os.path.join('jobs', job_type + '.sh.erb'),
			job_context
		)
		template.render(
			os.path.join(self.release_dir, 'jobs', job_name, 'monit'),
			os.path.join('jobs', 'monit'),
			job_context
		)

		self.context['jobs'] = self.context.get('jobs', []) + [{
			'name': job_name,
			'type': job_type,
			'package': package,
		}]
		if post_deploy:
			self.context['post_deploy_errands'] = self.context.get('post_deploy_errands', []) + [{ 'name': job_name }]
		if pre_delete:
			self.context['pre_delete_errands'] = self.context.get('pre_delete_errands', []) + [{ 'name': job_name }]

	def add_src_package(self, package, alternate_template=None):
		self.add_package_to_bosh('src', package, alternate_template)

	def add_blob_package(self, package, alternate_template=None):
		self.add_package_to_bosh('blobs', package, alternate_template)

	def add_package_to_bosh(self, dir, package, alternate_template=None):
		# Hmm...this possible renaming might break stuff...can we do it earlier?
		name = package['name'].lower().replace('-','_')
		package['name'] = name
		self.__bosh('generate', 'package', name)
		target_dir = os.path.realpath(os.path.join(self.release_dir, dir, name))
		package_dir = os.path.realpath(os.path.join(self.release_dir, 'packages', name))
		mkdir_p(target_dir)
		template_dir = 'packages'
		if alternate_template is not None:
			template_dir = os.path.join(template_dir, alternate_template)
		package_context = {
			'context': self.context,
			'package': package,
			'files': []
		}
		files = package.get('files', [])
		path = package.get('path', None)
		if path is not None:
			files += [ { 'path': path } ]
			package['path'] = os.path.basename(path)
		manifest = package.get('manifest', None)
		manifest_path = None
		if type(manifest) is dict:
			manifest_path = manifest.get('path', None)
		if manifest_path is not None:
			files += [ { 'path': manifest_path } ]
			package['manifest']['path'] = os.path.basename(manifest_path)
		for file in files:
			filename = file.get('name', os.path.basename(file['path']))
			file['name'] = filename
			download(file['path'], os.path.join(target_dir, filename), cache=self.context.get('cache', None))
			package_context['files'] += [ filename ]
		for docker_image in package.get('docker_images', []):
			filename = docker_image.lower().replace('/','-').replace(':','-') + '.tgz'
			download_docker_image(docker_image, os.path.join(target_dir, filename), cache=self.context.get('cache', None))
			package_context['files'] += [ filename ]
		if package.get('is_app', False):
			manifest = package.get('manifest', { 'name': name })
			if manifest.get('random-route', False):
				print('Illegal manifest option in package', name + ': random-route is not supported', file=sys.stderr)
				sys.exit(1)
			manifest_file = os.path.join(target_dir, 'manifest.yml')
			with open(manifest_file, 'wb') as f:
				f.write('---\n')
				f.write(yaml.safe_dump(manifest, default_flow_style=False))
			package_context['files'] += [ 'manifest.yml' ]
		template.render(
			os.path.join(package_dir, 'spec'),
			os.path.join(template_dir, 'spec'),
			package_context
		)
		template.render(
			os.path.join(package_dir, 'packaging'),
			os.path.join(template_dir, 'packaging'),
			package_context
		)

	def __bosh(self, *argv):
		argv = list(argv)
		print('bosh', ' '.join(argv))
		command = [ 'bosh', '--no-color', '--non-interactive' ] + argv
		try:
			return subprocess.check_output(command, stderr=subprocess.STDOUT, cwd=self.release_dir)
		except subprocess.CalledProcessError as e:
			if argv[0] == 'init' and argv[1] == 'release' and 'Release already initialized' in e.output:
				return e.output
			if argv[0] == 'generate' and 'already exists' in e.output:
				return e.output
			print(e.output)
			sys.exit(e.returncode)
