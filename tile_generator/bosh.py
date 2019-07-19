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
	from urllib.request import urlretrieve
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
			print('download bosh release', self.name)
			return self.download_tarball()
		return self.build_tarball()

	def download_tarball(self):
		def semver_x_greater_or_equal_to_y(x, y):
			# split the semver into major minor patch
			x = [int(d) for d in x.split('.')]
			y = [int(d) for d in y.split('.')]

			return x >= y

		mkdir_p(self.release_dir)
		tarball = os.path.join(self.release_dir, self.name + '.tgz')
		download(self.path, tarball, self.context.get('cache'))
		manifest = self.get_manifest(tarball)
		if manifest['name'] == 'cf-cli':
			# Enforce at least version 1.15 as prior versions have a CVE
			# https://docs.google.com/document/d/177QPJHKXMld1AD-GNHeildVfTGCWrGP-GSSlDmJY9eI/edit?ts=5ccd96fa
			if not semver_x_greater_or_equal_to_y(manifest['version'], '1.15.0'):
				raise RuntimeError('The cf-cli bosh release should be version 1.15.0 or higher. Detected %s' % manifest['version'])
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
		filename=self.name + '-' + self.context['version'] + '.tgz'

		args = ['create-release', '--force','--final', '--tarball', filename, '--version', self.context['version']]
		if self.context.get('sha1'):
			args.insert(3, '--sha2')

		self.tarball = self.__bosh(*args, capture='Release tarball')
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
			file_options = dict()
			for file in package.get('files', []):
				for key in [k for k in file.keys() if k not in ['name', 'path']]:
					file_options[key] = file[key]
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
			result = { 'path': zipfilename, 'name': os.path.basename(zipfilename) }
			result.update(file_options)
			package['files'] = [result]
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
	if not bosh_exec:
		print("'bosh' command should be on the path. See https://bosh.io for installation instructions")
		sys.exit(1)

	if bosh_exec:
		output = subprocess.check_output(["bosh", "--version"], stderr=subprocess.STDOUT, cwd=".")
		if output.startswith(b"version 1."):
			print("You are running an older version of bosh. Please upgrade to the latest version. See https://bosh.io/docs/cli-v2.html for installation instructions")
			sys.exit(1)

def run_bosh(working_dir, *argv, **kw):
	ensure_bosh()

	# Ensure that the working_dir is a git repo, needed for bosh's create-release.
	# This is used to avoid this bug https://www.pivotaltracker.com/story/show/159156765
	if 'create-release' in argv:
		print(working_dir)
		cmd = 'if ! git rev-parse --git-dir 2> /dev/null; then git init; fi'
		subprocess.call(cmd, shell=True, cwd=working_dir)

	# Change the commands
	argv = list(argv)
	print('bosh', ' '.join(argv))
	command = ['bosh', '--no-color', '--non-interactive'] + argv
	capture = kw.get('capture', None)
	try:
		output = subprocess.check_output(command, stderr=subprocess.STDOUT, cwd=working_dir)
		if capture is not None:
			for l in output.split(b'\n'):
				if l.startswith(bytes(capture, 'utf-8')):
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
