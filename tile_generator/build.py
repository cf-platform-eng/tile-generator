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
import template
import urllib
import zipfile
import yaml
import re
import datetime

from bosh import *
from util import *

LIB_PATH = os.path.dirname(os.path.realpath(__file__))
REPO_PATH = os.path.realpath(os.path.join(LIB_PATH, '..'))
DOCKER_BOSHRELEASE_VERSION = '23'

# FIXME dead code, remove.
def old_build(config, verbose=False):
	validate_config(config)
	context = config.copy()
	add_defaults(context)
	upgrade_config(context)
	context['verbose'] = verbose
	with cd('release', clobber=True):
		create_bosh_release(context)
	validate_memory_quota(context)
	with cd('product', clobber=True):
		create_tile(context)

def build(config, verbose=False):
	# Clean up config (as above)
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
			print >> sys.stderr, 'product name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens'
			sys.exit(1)
	except KeyError as e:
		print >> sys.stderr, 'tile.yml is missing mandatory property', e
		sys.exit(1)
	for package in config.get('packages', []):
		try:
			if validname.match(package['name']) is None:
				print >> sys.stderr, 'package name must start with a letter, be all lower-case letters or numbers, with words optionally seperated by hyphens'
				sys.exit(1)
		except KeyError as e:
			print >> sys.stderr, 'package is missing mandatory property', e
			sys.exit(1)
	return config

def upgrade_config(config):
	# v0.9 specified auto_services as a space-separated string of service names
	for package in config.get('packages', []):
		auto_services = package.get('auto_services', None)
		if auto_services is not None:
			if isinstance(auto_services, basestring):
				package['auto_services'] = [ { 'name': s } for s in auto_services.split()]
	# v0.9 expected a string manifest for docker-bosh releases
	for package in config.get('packages', []):
		if package.get('type') == 'docker-bosh':
			manifest = package.get('manifest')
			if manifest is not None and isinstance(manifest, basestring):
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
	print 'stemcell_criteria:'
	print '  os:', stemcell_criteria['os']
	print '  version:', stemcell_criteria['version']
	print
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
		print >> sys.stderr, 'Specified org quota of', specified, 'MB is insufficient'
		print >> sys.stderr, 'Required quota is at least the total package size of', context['total_memory'], 'MB'
		print >> sys.stderr, 'Plus enough room for blue/green deployment of the largest app:', context['max_memory'], 'MB'
		print >> sys.stderr, 'For a total of:', required, 'MB'
		sys.exit(1)

# FIXME dead code, remove.
def create_bosh_release(context):
	target = os.getcwd()
	bosh('init', 'release')
	template.render('src/templates/all_open.json', 'src/templates/all_open.json', context)
	template.render('src/common/utils.sh', 'src/common/utils.sh', context)
	template.render('config/final.yml', 'config/final.yml', context)
	packages = context.get('packages', [])
	requires_cf_cli = False
	requires_docker_bosh = False
	for package in packages:
		typename = package.get('type', None)
		if typename is None:
			print >>sys.stderr, 'Package', package['name'], 'does not have a type'
			sys.exit(1)
		typedef = ([ t for t in package_types if t['typename'] == typename ] + [ None ])[0]
		if typedef is None:
			print >>sys.stderr, 'Package', package['name'], 'has unknown type', typename
			print >>sys.stderr, 'Valid types are:', ', '.join([ t['typename'] for t in package_types])
			sys.exit(1)
		for flag in typedef['flags']:
			package[flag] = True
		if package.get('is_bosh_release', False):
			add_bosh_release(context, package)
		else:
			add_blob_package(context, package)
		for job in typedef.get('jobs', []):
			add_bosh_job(
				context,
				package,
				job.lstrip('+-'),
				post_deploy=job.startswith('+'),
				pre_delete=job.startswith('-')
			)
		requires_cf_cli |= package.get('requires_cf_cli', False)
		requires_docker_bosh |= package.get('requires_docker_bosh', False)
	if requires_cf_cli:
		add_cf_cli(context)
		add_bosh_job(context, None, 'deploy-all', post_deploy=True)
		add_bosh_job(context, None, 'delete-all', pre_delete=True)
	add_common_utils(context)
	bosh('upload', 'blobs')
	output = bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', context['version'])
	context['release'] = bosh_extract(output, [
		{ 'label': 'name', 'pattern': 'Release name' },
		{ 'label': 'version', 'pattern': 'Release version' },
		{ 'label': 'manifest', 'pattern': 'Release manifest' },
		{ 'label': 'tarball', 'pattern': 'Release tarball' },
	])
	context['requires_docker_bosh'] = requires_docker_bosh
	context['requires_cf_cli'] = requires_cf_cli
	print

# FIXME dead code, remove.
def add_bosh_job(context, package, job_type, post_deploy=False, pre_delete=False):
	errand = False
	if post_deploy or pre_delete:
		errand = True
	job_name = job_type
	if package is not None:
		job_name += '-' + package['name']

	bosh('generate', 'job', job_name)
	job_context = {
		'job_name': job_name,
		'job_type': job_type,
		'context': context,
		'package': package,
		'errand': errand,
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

	context['jobs'] = context.get('jobs', []) + [{
		'name': job_name,
		'type': job_type,
		'package': package,
	}]
	if post_deploy:
		context['post_deploy_errands'] = context.get('post_deploy_errands', []) + [{ 'name': job_name }]
	if pre_delete:
		context['pre_delete_errands'] = context.get('pre_delete_errands', []) + [{ 'name': job_name }]

# FIXME dead code, remove.
def add_src_package(context, package, alternate_template=None):
	add_package('src', context, package, alternate_template)

# FIXME dead code, remove.
def add_blob_package(context, package, alternate_template=None):
	add_package('blobs', context, package, alternate_template)

# FIXME dead code, remove.
def add_package(dir, context, package, alternate_template=None):
	name = package['name'].lower().replace('-','_')
	package['name'] = name
	bosh('generate', 'package', name)
	target_dir = os.path.realpath(os.path.join(dir, name))
	package_dir = os.path.realpath(os.path.join('packages', name))
	mkdir_p(target_dir)
	template_dir = 'packages'
	if alternate_template is not None:
		template_dir = os.path.join(template_dir, alternate_template)
	package_context = {
		'context': context,
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
			urllib.urlretrieve(file['path'], os.path.join(target_dir, filename))
			package_context['files'] += [ filename ]
		for docker_image in package.get('docker_images', []):
			filename = docker_image.lower().replace('/','-').replace(':','-') + '.tgz'
			download_docker_image(docker_image, os.path.join(target_dir, filename), cache=context.get('docker_cache', None))
			package_context['files'] += [ filename ]
	if package.get('is_app', False):
		manifest = package.get('manifest', { 'name': name })
		if manifest.get('random-route', False):
			print >> sys.stderr, 'Illegal manifest option in package', name + ': random-route is not supported'
			sys.exit(1)
		manifest_file = os.path.join(target_dir, 'manifest.yml')
		with open(manifest_file, 'wb') as f:
			f.write('---\n')
			f.write(yaml.safe_dump(manifest, default_flow_style=False))
		package_context['files'] += [ 'manifest.yml' ]
		update_memory(context, manifest)
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

# FIXME dead code, remove.
def add_cf_cli(context):
	add_blob_package(context,
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
	context['requires_product_versions'] = context.get('requires_product_versions', []) + [
		{
			'name': 'cf',
			'version': '~> 1.5'
		}
	]

# FIXME dead code, remove.
def add_common_utils(context):
	add_src_package(context,
		{
			'name': 'common',
			'files': []
		},
		alternate_template='common'
	)

# FIXME dead code, remove.
def create_tile(context):
	release = context['release']
	release['file'] = os.path.basename(release['tarball'])
	with cd('releases'):
		print 'tile import release', release['name']
		shutil.copy(release['tarball'], release['file'])
		if context.get('requires_docker_bosh', False):
			print 'tile import release docker'
			docker_release = download_docker_release()
			context['docker_release'] = docker_release
	print 'tile generate metadata'
	template.render('metadata/' + release['name'] + '.yml', 'tile/metadata.yml', context)
	print 'tile generate content-migrations'
	template.render('content_migrations/' + release['name'] + '.yml', 'tile/content-migrations.yml', context)
	print 'tile generate migrations'
	migrations = 'migrations/v1/' + datetime.datetime.now().strftime('%Y%m%d%H%M') + '_noop.js'
	template.render(migrations, 'tile/migration.js', context)
	print 'tile generate package'
	pivotal_file = release['name'] + '-' + release['version'] + '.pivotal'
	with zipfile.ZipFile(pivotal_file, 'w') as f:
		f.write(os.path.join('releases', release['file']))
		if context.get('requires_docker_bosh', False):
			docker_release = context['docker_release']
			f.write(os.path.join('releases', docker_release['file']))
		for bosh_release in context.get('bosh_releases', []):
			print 'tile import release', bosh_release['name']
			shutil.copy(bosh_release['tarball'], os.path.join('releases', bosh_release['file']))
			f.write(os.path.join('releases', bosh_release['file']))
		f.write(os.path.join('metadata', release['name'] + '.yml'))
		f.write(os.path.join('content_migrations', release['name'] + '.yml'))
		f.write(migrations)
	print
	print 'created tile', pivotal_file

# FIXME dead code, remove.
def add_bosh_release(context, package):
	with cd('..'):
		tarball = os.path.realpath(package['path'])
	release_file = os.path.basename(tarball)
	with tarfile.open(tarball) as tar:
		manifest_file = tar.extractfile('./release.MF')
		manifest = yaml.safe_load(manifest_file)
		manifest_file.close()
		release_name = manifest['name']
		release_version = manifest['version']
	context['bosh_releases'] = context.get('bosh_releases', []) + [
		{
			'tarball': tarball,
			'file': release_file,
			'name': release_name,
			'version': release_version,
		}
	]

# FIXME dead code, remove.
def bosh(*argv):
	argv = list(argv)
	print 'bosh', ' '.join(argv)
	command = [ 'bosh', '--no-color', '--non-interactive' ] + argv
	try:
		return subprocess.check_output(command, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError as e:
		if argv[0] == 'init' and argv[1] == 'release' and 'Release already initialized' in e.output:
			return e.output
		if argv[0] == 'generate' and 'already exists' in e.output:
			return e.output
		print e.output
		sys.exit(e.returncode)

# FIXME dead code, remove.
def bash(*argv):
	argv = list(argv)
	try:
		return subprocess.check_output(argv, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError as e:
		print ' '.join(argv), 'failed'
		print e.output
		sys.exit(e.returncode)

def is_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+([\\-+][0-9a-zA-Z]+(\\.[0-9a-zA-Z]+)*)*$')
	return valid.match(version) is not None

def is_unannotated_semver(version):
	valid = re.compile('[0-9]+\\.[0-9]+\\.[0-9]+$')
	return valid.match(version) is not None

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
