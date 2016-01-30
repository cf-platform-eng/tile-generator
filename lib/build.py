#!/usr/bin/env python

import os
import sys
import errno
import shutil
import subprocess
import template
import urllib
import zipfile

LIB_PATH = os.path.dirname(os.path.realpath(__file__))
REPO_PATH = os.path.realpath(os.path.join(LIB_PATH, '..'))

def build(config, verbose=False):
	context = config.copy()
	add_defaults(context)
	context['verbose'] = verbose
	with cd('release', clobber=True):
		create_bosh_release(context)
	with cd('product', clobber=True):
		create_tile(context)

def add_defaults(context):
	context['stemcell_criteria'] = context.get('stemcell_criteria', {})
	context['all_properties'] = context.get('properties', [])
	for form in context.get('forms', []):
		properties = form.get('properties', [])
		for property in properties:
			property['configurable'] = 'true'
		context['all_properties'] += properties
	for property in context['all_properties']:
		property['name'] = property['name'].lower().replace('-','_')

package_types = [
	# A + at the start of the job type indicates it is a post-deploy errand
	# A - at the start of the job type indicates it is a pre-delete errand
	{
		'typename': 'app',
		'flags': [ 'requires_cf_cli', 'is_app' ],
		'jobs':  [ '+deploy-app', '-delete-app' ],
	},
	{
		'typename': 'app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app' ],
		'jobs':  [ '+deploy-app', '-delete-app', '+register-broker', '-destroy-broker' ],
	},
	{
		'typename': 'external-broker',
		'flags': [ 'is_broker', 'is_external_broker' ],
		'jobs':  [ '+register-broker', '-destroy-broker' ],
	},
	{
		'typename': 'buildpack',
		'flags': [ 'requires_cf_cli', 'is_buildpack' ],
		'jobs':  [ '+deploy-buildpack', '-delete-buildpack' ],
	},
	{
		'typename': 'docker-bosh',
		'flags': [ 'requires_docker_bosh', 'is_docker_bosh', 'is_docker' ],
		'jobs':  [ 'docker-image-uploader' ],
	},
	{
		'typename': 'docker-app',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_docker_app', 'is_docker' ],
		'jobs':  [ '+deploy-app', '-delete-app' ],
	},
	{
		'typename': 'docker-app-broker',
		'flags': [ 'requires_cf_cli', 'is_app', 'is_broker', 'is_broker_app', 'is_docker_app', 'is_docker' ],
		'jobs':  [ '+deploy-app', '-delete-app', '+register-broker', '-destroy-broker' ],
	},
	{
		'typename': 'blob',
		'flags': [ 'is_blob' ],
		'jobs':  [],
	},
]

def create_bosh_release(context):
	target = os.getcwd()
	bosh('init', 'release')
	template.render('src/templates/all_open.json', 'src/templates/all_open.json', context)
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
		add_blob_package(context, package)
		for flag in typedef['flags']:
			package[flag] = True
		for job in typedef['jobs']:
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
	bosh('upload', 'blobs')
	output = bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', context['version'])
	context['release'] = bosh_extract(output, [
		{ 'label': 'name', 'pattern': 'Release name' },
		{ 'label': 'version', 'pattern': 'Release version' },
		{ 'label': 'manifest', 'pattern': 'Release manifest' },
		{ 'label': 'tarball', 'pattern': 'Release tarball' },
	])
	context['requires_docker_bosh'] = requires_docker_bosh;
	print

def add_bosh_job(context, package, job_type, post_deploy=False, pre_delete=False):
	job_name = job_type + '-' + package['name']
	bosh('generate', 'job', job_name)
	job_context = {
		'job_name': job_name,
		'job_type': job_type,
		'context': context,
		'package': package,
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
	  job_context)

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
		for file in package.get('files', []):
			filename = file.get('name', os.path.basename(file['path']))
			try:
				urllib.urlretrieve(file['path'], os.path.join(target_dir, filename))
			except ValueError: # Invalid URL, assume filename
				shutil.copy(os.path.join('..', file['path']), target_dir)
			package_context['files'] += [ filename ]
			file['name'] = filename
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
				'path': 'https://cli.run.pivotal.io/stable?release=linux64-binary&source=github-rel'
			}]
		},
		alternate_template='cf_cli'
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
	print 'tile generate package'
	pivotal_file = release['name'] + '-' + release['version'] + '.pivotal'
	with zipfile.ZipFile(pivotal_file, 'w') as f:
		f.write(os.path.join('releases', release['file']))
		f.write(os.path.join('metadata', release['name'] + '.yml'))
		f.write(os.path.join('content_migrations', release['name'] + '.yml'))
	print
	print 'created tile', pivotal_file

def download_docker_release():
	release_name = 'docker'
	release_version = '23'
	release_file = release_name + '-boshrelease-' + release_version + '.tgz'
	release_tarball = release_file
	if not os.path.isfile(release_tarball):
		url = 'http://bosh.io/d/github.com/cf-platform-eng/docker-boshrelease?v=' + release_version
		urllib.urlretrieve(url, release_tarball)
	return {
		'tarball': release_tarball,
		'name': release_name,
		'version': release_version,
		'file': release_file,
	}

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
