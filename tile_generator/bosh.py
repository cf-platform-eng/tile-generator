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
def download_docker_release(version=None):
	version_param = '?v=' + version if version else ''
	url = 'https://bosh.io/d/github.com/cf-platform-eng/docker-boshrelease' + version_param
	localfile = 'docker-boshrelease.tgz'
	download(url, localfile)
	manifest = read_release_manifest(localfile)
	print("Downloaded docker version", manifest['version'], file=sys.stderr)
	return {
		'tarball': localfile,
		'name': manifest['name'],
		'version': manifest['version'],
		'file': localfile,
	}

class BoshReleases:

	def __init__(self, context):
		self.context = context
		# FIXME pass in target dir instead of relying on CWD.
		# self.releases_dir = releases_dir
		self.releases = {} # Map from name to BoshRelease object.
		# self.requires_cf_cli = False
		# self.requires_docker_bosh = False
		self.context['requires_docker_bosh'] = False
		# self.context['bosh_releases'] = [] # FIXME Get rid of this contex entry, move info into BoshRelease instances.

	def add_package(self, package):
		print("tile adding package", package['name'])
		typename = package.get('type', None)
		typedef = ([ t for t in package_types if t['typename'] == typename ] + [ None ])[0]
		flags = typedef.get('flags', [])
		jobs = typedef.get('jobs', [])
		bosh_release_name = package['name'] if package.get('is_bosh_release', False) else self.context['name']
		if not bosh_release_name in self.releases:
			release = BoshRelease(bosh_release_name, self.context)
			self.releases[bosh_release_name] = release
		release = self.releases[bosh_release_name]
		release.add_package(package, flags, jobs)
		# self.requires_cf_cli |= release.has_flag('requires_cf_cli')
		self.context['requires_docker_bosh'] = self.context.get('requires_docker_bosh', False) | release.has_flag('requires_docker_bosh')
		# FIXME Move this out of global context into the BoshRelease class.
		# Cf related comment in BoshRelease.add_packge.
		if release.has_flag('is_bosh_release'):
			self.context['bosh_releases'] = self.context.get('bosh_releases', []) + [
				{
					'tarball': release.tarball,
					'file': release.file,
					'name': release.name,
					'version': release.version,

				}
			]

	def create_tile(self):
		release_info = {}
		for name in self.releases:
			release = self.releases[name]
			with cd(release.release_dir):
				release_info.update(self.releases[name].pre_create_tile())
		if 'tarball' in release_info:
			release_info['file'] = os.path.basename(release_info['tarball'])
		self.context['release'] = release_info
		# Can we just compute release_info instead of parsing from bosh in pre_create_tile?
		release_name = release_info.get('name', self.context.get('name', None))
		release_version = release_info.get('version', self.context.get('version', None))
		# FIXME Don't treat the docker bosh release specially; just add it as another BoshRelease.
		if self.context['requires_docker_bosh']:
			with cd('releases'):
				print('tile import release docker')
				docker_release = download_docker_release(version=self.context.get('docker_bosh_version', None))
				self.context['docker_release'] = docker_release
		print('tile generate metadata')
		template.render('metadata/' + release_name + '.yml', 'tile/metadata.yml', self.context)
		print('tile generate content-migrations')
		template.render('content_migrations/' + release_name + '.yml', 'tile/content-migrations.yml', self.context)
		print('tile generate migrations')
		migrations = 'migrations/v1/' + datetime.datetime.now().strftime('%Y%m%d%H%M') + '_noop.js'
		template.render(migrations, 'tile/migration.js', self.context)
		print('tile generate package')
		pivotal_file = release_name + '-' + release_version + '.pivotal'
		with zipfile.ZipFile(pivotal_file, 'w') as f:
			if self.context['requires_docker_bosh']:
				docker_release = self.context['docker_release']
				f.write(os.path.join('releases', docker_release['file']))
			for name in self.releases:
				release = self.releases[name]
				print('tile import release', name)
				mkdir_p('releases')
				shutil.copy(release.tarball, os.path.join('releases', release.file))
				f.write(os.path.join('releases', release.file))
			f.write(os.path.join('metadata', release_name + '.yml'))
			f.write(os.path.join('content_migrations', release_name + '.yml'))
			f.write(migrations)
		print()
		print('created tile', pivotal_file)


class BoshRelease:

	def __init__(self, name, context):
		self.release_dir = os.getcwd() # FIXME parameterize
		self.name = name
		self.flags = []
		self.jobs = []
		self.packages = []
		self.context = context

	def has_flag(self, flag):
		return flag in self.flags

	def add_package(self, package, flags, jobs):
		self.packages.append(package)
		self.flags += flags
		for job in jobs:
			self.jobs.append({'name': job, 'package': package})
		# FIXME this is pretty ugly...would like a subclass for is_bosh_release, but
		# want minimal code change for now.
		if 'is_bosh_release' in flags:
			with cd('..'):
				self.tarball = os.path.realpath(self.packages[0]['path'])
				self.file = os.path.basename(self.tarball)
				manifest = read_release_manifest(self.tarball)
				self.name = manifest['name']
				self.version = manifest['version']
		if 'is_app' in flags:
			manifest = package.get('manifest', { 'name': package['name'] })
			update_memory(self.context, manifest)

	# Build the bosh release, if needed.
	def pre_create_tile(self):
		if self.has_flag('is_bosh_release'):
			print("tile", self.name, "bosh release already built")
			return {}
		print("tile building bosh release for", self.name)
		self.__bosh('init', 'release')
		template.render('src/templates/all_open.json', 'src/templates/all_open.json', self.context)
		template.render('src/common/utils.sh', 'src/common/utils.sh', self.context)
		template.render('config/final.yml', 'config/final.yml', self.context)
		for package in self.packages:
			self.add_blob_package(package)
		for job in self.jobs:
			self.add_bosh_job(
				job['package'],
				job['name'].lstrip('+-'),
				post_deploy=job['name'].startswith('+'),
				pre_delete=job['name'].startswith('-')
			)
		if self.has_flag('requires_cf_cli'):
			self.add_cf_cli()
			self.add_bosh_job(None, 'deploy-all', post_deploy=True)
			self.add_bosh_job(None, 'delete-all', pre_delete=True)
		self.add_common_utils()
		self.__bosh('upload', 'blobs')
		output = self.__bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', self.context['version'])
		release_info = bosh_extract(output, [
			{ 'label': 'name', 'pattern': 'Release name' },
			{ 'label': 'version', 'pattern': 'Release version' },
			{ 'label': 'manifest', 'pattern': 'Release manifest' },
			{ 'label': 'tarball', 'pattern': 'Release tarball' },
		])
		self.tarball = release_info['tarball']
		self.file = os.path.basename(self.tarball)
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
			'files': []
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
			os.path.join('jobs', job_name, 'spec'),
			os.path.join('jobs', 'spec'),
			job_context
		)
		template.render(
			os.path.join('jobs', job_name, 'templates', job_name + '.sh.erb'),
			os.path.join('jobs', job_type + '.sh.erb'),
			job_context
		)
		template.render(
			os.path.join('jobs', job_name, 'monit'),
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
		target_dir = os.path.realpath(os.path.join(dir, name))
		package_dir = os.path.realpath(os.path.join('packages', name))
		mkdir_p(target_dir)
		template_dir = 'packages'
		if alternate_template is not None:
			template_dir = os.path.join(template_dir, alternate_template)
		package_context = {
			'context': self.context,
			'package': package,
			'files': []
		}
		with cd('..'):
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
				urlretrieve(file['path'], os.path.join(target_dir, filename))
				package_context['files'] += [ filename ]
			for docker_image in package.get('docker_images', []):
				filename = docker_image.lower().replace('/','-').replace(':','-') + '.tgz'
				download_docker_image(docker_image, os.path.join(target_dir, filename), cache=self.context.get('docker_cache', None))
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
