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
import tempfile
from distutils import spawn
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

class BoshRelease:

	def __init__(self, release, context):
		self.name = release['name']
		self.release_dir = os.path.join('release', self.name)
		self.path = release.get('path', None)
		self.jobs = release.get('jobs', [])
		self.packages = release.get('packages', [])
		self.context = context
		self.config = release
		self.tarball = None

	def get_metadata(self):
		tarball = self.get_tarball()
		manifest = self.get_manifest(tarball)
		return {
			'release_name': manifest['name'],
			'version': manifest['version'],
			'tarball': tarball,
			'file': os.path.basename(tarball),
		}

	def get_manifest(self, tarball):
		with tarfile.open(tarball) as tar:
			if './release.MF' in tar.getnames():
				manifest_file = tar.extractfile('./release.MF')
			elif 'release.MF' in tar.getnames():
				manifest_file = tar.extractfile('release.MF')
			else:
				raise Exception('No release manifest found in ' + tarball)
			manifest = yaml.safe_load(manifest_file)
			manifest_file.close()
			return manifest

	def get_tarball(self):
		if self.tarball is not None and os.path.isfile(self.tarball):
			return self.tarball
		if self.path is not None:
			print('bosh download release', self.name)
			return self.download_tarball()
		return self.build_tarball()

	def download_tarball(self):
		mkdir_p(self.release_dir)
		tarball = os.path.join(self.release_dir, self.name + '.tgz')
		download(self.path, tarball, self.context.get('cache', None))
		manifest = self.get_manifest(tarball)
		self.tarball = os.path.join(self.release_dir, manifest['name'] + '-' + manifest['version'] + '.tgz')
		os.rename(tarball, self.tarball)
		return self.tarball

	def build_tarball(self):
		mkdir_p(self.release_dir)

		self.__bosh('init-release')
		template.render(
			os.path.join(self.release_dir, 'config/final.yml'),
			'config/final.yml',
			self.context)

		for package in self.packages:
			self.add_package(package)

		for job in self.jobs:
			self.add_job(job)
		self.__bosh('upload-blobs')
		filename=self.name+'-'+self.context['version'] + '.tgz'

		if self.context.get('sha1'):
			self.tarball = self.__bosh('create-release', '--force','--final', '--tarball',filename, '--version', self.context['version'], capture='Release tarball')
		else:
			self.tarball = self.__bosh('create-release', '--force','--sha2', '--final', '--tarball',filename, '--version', self.context['version'], capture='Release tarball')


		self.tarball = os.path.join(self.release_dir,filename)
		return self.tarball

	def add_job(self, job):
		job_name = job['name']
		job_type = job.get('type', job_name)
		job_template = job.get('template', job_type)
		is_errand = job.get('lifecycle', None) == 'errand'
		package = job.get('package', None)
		packages = job.get('packages', [])
		self.__bosh('generate-job', job_type)
		job_context = {
			'job_name': job_name,
			'job_type': job_type,
			'context': self.context,
			'package': package,
			'packages': packages,
			'errand': is_errand,
		}
		template.render(
			os.path.join(self.release_dir, 'jobs', job_type, 'spec'),
			os.path.join('jobs', 'spec'),
			job_context
		)
		template.render(
			os.path.join(self.release_dir, 'jobs', job_type, 'templates', job_type + '.sh.erb'),
			os.path.join('jobs', job_template + '.sh.erb'),
			job_context
		)
		template.render(
			os.path.join(self.release_dir, 'jobs', job_type, 'templates', 'opsmgr.env.erb'),
			os.path.join('jobs', 'opsmgr.env.erb'),
			job_context
		)
		template.render(
			os.path.join(self.release_dir, 'jobs', job_type, 'monit'),
			os.path.join('jobs', 'monit'),
			job_context
		)

	def needs_zip(self, package):
		# Only zip package types that require single files
		if not package.get('is_cf', False) and not package.get('zip_if_needed', False):
			return False
		files = package['files']
		# ...if it has more than one file...
		if len(files) > 1:
			return True
		# ...or a single file is not already a zip.
		elif len(files) == 1:
			return not zipfile.is_zipfile(files[0]['path'])
		return False

	def add_blob(self,package):
		for file in package ['files']:
			self.__bosh('add-blob',os.path.realpath(file['path']),file['name'])

	def add_package(self, package):
		name = package['name']
		dir = package.get('dir', 'blobs')
		self.__bosh('generate-package', name)
		target_dir = os.path.realpath(os.path.join(self.release_dir, dir, name))
		package_dir = os.path.realpath(os.path.join(self.release_dir, 'packages', name))
		mkdir_p(target_dir)
		template_dir = 'packages'
		# Download files for package
		if self.needs_zip(package):
			staging_dir = tempfile.mkdtemp()
			for file in package.get('files', []):
				download(file['path'], os.path.join(staging_dir, file['name']), cache=self.context.get('cache', None))
			path = package.get('manifest', {}).get('path', '')
			dir_to_zip = os.path.join(staging_dir, path) if path else staging_dir
			zipfilename = os.path.realpath(os.path.join(target_dir, package['name'] + '.zip'))
			zip_dir(zipfilename, dir_to_zip)
			shutil.rmtree(staging_dir)
			newpath = os.path.basename(zipfilename)
			for job in self.jobs:
				if job.get('manifest', {}).get(package['name'], {}).get('app_manifest'):
					job['manifest'][package['name']]['app_manifest']['path'] = newpath
			package['files'] = [{ 'path': zipfilename, 'name': os.path.basename(zipfilename) }]
			self.__bosh('add-blob',zipfilename,os.path.join(name,os.path.basename(zipfilename)))
		else:
			for file in package.get('files', []):
				download(file['path'], os.path.join(target_dir, file['name']), cache=self.context.get('cache', None))
				self.__bosh('add-blob',os.path.join(target_dir, file['name']),os.path.join(name,file['name']))
		# Construct context for template rendering
		package_context = {
			'context': self.context,
			'package': package,
			'files': package.get('files', []),
		}
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

	def __bosh(self, *argv, **kw):
		return run_bosh(self.release_dir, *argv, **kw)


def ensure_bosh():
	bosh_exec = spawn.find_executable('bosh')
	## check the version
	## bosh --version
	## version 2.0.1-74fad57-2017-02-15T20:17:00Z
	##
	## Succeeded
	## bosh --version
	## BOSH 1.3262.26.0

	if not bosh_exec:
		print("'bosh' command should be on the path. See https://bosh.io for installation instructions")
		sys.exit(1)

	if bosh_exec:
		output = subprocess.check_output(["bosh", "--version"], stderr=subprocess.STDOUT, cwd=".")
		if not output.startswith("version 2.") and not output.startswith("version 3."):
			print("You are running older bosh version. Please upgrade to bosh 2.0 or later. See https://bosh.io/docs/cli-v2.html for installation instructions")
			sys.exit(1)

def run_bosh(working_dir, *argv, **kw):
	ensure_bosh()
	## change the commands
	argv = list(argv)
	print('bosh', ' '.join(argv))
	command = ['bosh', '--no-color', '--non-interactive'] + argv
	capture = kw.get('capture', None)
	try:
		output = subprocess.check_output(command, stderr=subprocess.STDOUT, cwd=working_dir)
		if capture is not None:
			for l in output.split('\n'):
				if l.startswith(capture):
					output = l.split(':', 1)[-1].strip()
					break
		return output
	except subprocess.CalledProcessError as e:
		if argv[0] == 'init' and argv[1] == 'release' and 'Release already initialized' in e.output:
			return e.output
		if argv[0] == 'generate' and 'already exists' in e.output:
			return e.output
		print(e.output)
		sys.exit(e.returncode)
