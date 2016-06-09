#!/usr/bin/env python

import os
import sys
import errno
import requests
import shutil
import subprocess
import template
import urllib
import zipfile
import yaml
import re
import datetime

LIB_PATH = os.path.dirname(os.path.realpath(__file__))
REPO_PATH = os.path.realpath(os.path.join(LIB_PATH, '..'))
DOCKER_BOSHRELEASE_VERSION = '23'

def build(config, verbose=False):
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
	context['stemcell_criteria'] = context.get('stemcell_criteria', {})
	context['all_properties'] = context.get('properties', [])
	context['total_memory'] = 0
	context['max_memory'] = 0
	for form in context.get('forms', []):
		properties = form.get('properties', [])
		for property in properties:
			property['configurable'] = 'true'
		context['all_properties'] += properties
	for property in context['all_properties']:
		property['name'] = property['name'].lower().replace('-','_')

def update_memory(context, manifest):
	memory = manifest.get('memory', '1G')
	unit = memory.lstrip('0123456789').lstrip(' ').lower()
	if unit not in [ 'g', 'gb', 'm', 'mb' ]:
		print >> sys.stderr, 'invalid memory size unit', unit, 'in', memory
		sys.exit(1)
	memory = int(memory[:-len(unit)])
	if unit in [ 'g', 'gb' ]:
		memory *= 1024
	context['total_memory'] += memory
	if memory > context['max_memory']:
		context['max_memory'] = memory

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

package_types = [
	# A + at the start of the job type indicates it is a post-deploy errand
	# A - at the start of the job type indicates it is a pre-delete errand
	{
		'typename': 'app',
		'flags': [ 'requires_cf_cli', 'is_app' ],
	},
	{
		'typename': 'app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app' ],
	},
	{
		'typename': 'external-broker',
		'flags': [ 'requires_cf_cli', 'is_broker', 'is_external_broker' ],
	},
	{
		'typename': 'buildpack',
		'flags': [ 'requires_cf_cli', 'is_buildpack' ],
	},
	{
		'typename': 'docker-bosh',
		'flags': [ 'requires_docker_bosh', 'is_docker_bosh', 'is_docker' ],
		'jobs':  [ 'docker-bosh' ],
	},
	{
		'typename': 'docker-app',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_docker_app', 'is_docker' ],
	},
	{
		'typename': 'docker-app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app', 'is_docker_app', 'is_docker' ],
	},
	{
		'typename': 'blob',
		'flags': [ 'is_blob' ],
	},
	{
		'typename': 'bosh-release',
		'flags': [ 'is_bosh_release' ],
	}
]

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

def add_src_package(context, package, alternate_template=None):
	add_package('src', context, package, alternate_template)

def add_blob_package(context, package, alternate_template=None):
	add_package('blobs', context, package, alternate_template)

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

def add_common_utils(context):
	add_src_package(context,
		{
			'name': 'common',
			'files': []
		},
		alternate_template='common'
	)

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

def download_docker_release():
	release_name = 'docker'
	release_version = DOCKER_BOSHRELEASE_VERSION
	release_file = release_name + '-boshrelease-' + release_version + '.tgz'
	release_tarball = release_file
	if not os.path.isfile(release_tarball):
		url = 'https://bosh.io/d/github.com/cf-platform-eng/docker-boshrelease?v=' + release_version
		download(url, release_tarball)
	return {
		'tarball': release_tarball,
		'name': release_name,
		'version': release_version,
		'file': release_file,
	}

def add_bosh_release(context, package):
	try:
		release_file = os.path.basename(package['path']) # my_bosh_release-6.tgz
		basename = release_file.rsplit('.', 1)[0] # my_bosh_release-6
		release_name = basename.rsplit('-', 1)[0] # my_bosh_release
		release_version = basename.rsplit('-', 1)[1] # 6
	except Exception as e:
		print >> sys.stderr, "bosh-release must have a path attribute of the form <name>_<version>.tgz"
		sys.exit(1)
	with cd('..'):
		context['bosh_releases'] = context.get('bosh_releases', []) + [
			{
				'tarball': os.path.realpath(package['path']),
				'file': release_file,
				'name': release_name,
				'version': release_version,
			}
		]

def download_docker_image(docker_image, target_file, cache=None):
	try:
		from docker.client import Client
		from docker.utils import kwargs_from_env
		kwargs = kwargs_from_env()
		kwargs['tls'].assert_hostname = False
		docker_cli = Client(**kwargs)
		image = docker_cli.get_image(docker_image)
		image_tar = open(target_file,'w')
		image_tar.write(image.data)
		image_tar.close()
	except Exception as e:
		if cache is not None:
			cached_file = os.path.join(cache, docker_image.lower().replace('/','-').replace(':','-') + '.tgz')
			if os.path.isfile(cached_file):
				print 'using cached version of', docker_image
				urllib.urlretrieve(cached_file, target_file)
				return
			print >> sys.stderr, docker_image, 'not found in cache', cache
			sys.exit(1)
		if isinstance(e, KeyError):
			print >> sys.stderr, 'docker not configured on this machine (or environment variables are not properly set)'
		else:
			print >> sys.stderr, docker_image, 'not found on local machine'
			print >> sys.stderr, 'you must either pull the image, or download it and use the --docker-cache option'
		sys.exit(1)

def bosh_extract(output, properties):
	result = {}
	for l in output.split('\n'):
		for p in properties:
			if l.startswith(p['pattern']):
				result[p['label']] = l.split(':', 1)[-1].strip()
	return result

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

def bash(*argv):
	argv = list(argv)
	try:
		return subprocess.check_output(argv, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError as e:
		print ' '.join(argv), 'failed'
		print e.output
		sys.exit(e.returncode)

def is_semver(version):
	semver = version.split('.')
	if len(semver) != 3:
		return False
	try:
		int(semver[0])
		int(semver[1])
		int(semver[2])
		return True
	except:
		return False

def update_version(history, version):
	if version is None:
		version = 'patch'
	prior_version = history.get('version', None)
	if prior_version is not None:
		history['history'] = history.get('history', [])
		history['history'] += [ prior_version ]
	if not is_semver(version):
		semver = history.get('version', '0.0.0')
		if not is_semver(semver):
			print >>sys.stderr, 'Version must be in semver format (x.y.z), instead found', semver
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

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath, clobber=False):
    	self.clobber = clobber
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        if self.clobber and os.path.isdir(self.newPath):
			shutil.rmtree(self.newPath)
        mkdir_p(self.newPath)
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)

def mkdir_p(dir):
   try:
      os.makedirs(dir)
   except os.error, e:
      if e.errno != errno.EEXIST:
         raise

def download(url, filename):
	response = requests.get(url, stream=True)
	with open(filename, 'wb') as file:
		for chunk in response.iter_content(chunk_size=1024):
			if chunk:
				file.write(chunk)
