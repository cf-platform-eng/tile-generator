#!/usr/bin/env python

import os
import sys
import errno
import shutil
import subprocess
import template
import urllib
import zipfile

PATH = os.path.dirname(os.path.realpath(__file__))
SABHA_PATH = os.path.realpath(os.path.join(PATH, '..', 'bosh-generic-sb-release', 'bin'))

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

def create_bosh_release(context):
	target = os.getcwd()
	bosh('init', 'release')
	template.render('src/templates/all_open.json', 'src/templates/all_open.json', context)
	template.render('config/final.yml', 'config/final.yml', context)
	packages = context.get('packages', [])
	requires_cf_cli = False
	for package in packages:
		add_blob_package(context, package)
		jobs = package.get('jobs', [])
		cf_push = False
		cf_create_service_broker = False
		cf_create_buildpack = False
		for job in jobs:
			if job == 'cf-push':
				requires_cf_cli = True
				package['is_app'] = True
				add_bosh_job(context, package, 'deploy-app', post_deploy=True)
				add_bosh_job(context, package, 'delete-app', pre_delete=True)
			elif job == 'cf-create-service-broker':
				requires_cf_cli = True
				package['is_broker'] = True
				add_bosh_job(context, package, 'register-broker', post_deploy=True)
				add_bosh_job(context, package, 'destroy-broker', pre_delete=True)
			elif job == 'cf-create-buildpack':
				requires_cf_cli = True
				add_bosh_job(context, package, 'deploy-buildpack', post_deploy=True)
				add_bosh_job(context, package, 'delete-buildpack', pre_delete=True)
			else:
				print >>sys.stderr, 'unknown job type', job, 'for', package.get('name', 'unnamed package')
				sys.exit(1)
		if package.get('is_app', False) and package.get('is_broker', False):
			package['is_broker_app'] = True
		if package.get('is_broker', False) and not package.get('is_app', False):
			package['is_external_broker'] = True
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

def bash(*argv):
	argv = list(argv)
	print ' '.join(argv)
	command = [ os.path.join(SABHA_PATH, argv[0]) ] + argv[1:]
	try:
		result = subprocess.check_output(command, stderr=subprocess.STDOUT)
		if VERBOSE:
			print '    ' + '\n    '.join(result.split('\n'))
		return result
	except subprocess.CalledProcessError as e:
		print e.output
		sys.exit(e.returncode)

def create_tile(context):
	release = context['release']
	release['file'] = os.path.basename(release['tarball'])
	with cd('releases'):
		print 'tile generate release'
		shutil.copy(release['tarball'], release['file'])
	print 'tile generate metadata'
	template.render('metadata/' + release['name'] + '.yml', 'tile/metadata.yml', context)
	print 'tile generate content-migrations'
	template.render('content_migrations/' + release['name'] + '.yml', 'tile/content-migrations.yml', context)
	print 'tile package'
	pivotal_file = release['name'] + '-' + release['version'] + '.pivotal'
	with zipfile.ZipFile(pivotal_file, 'w') as f:
		f.write(os.path.join('releases', release['file']))
		f.write(os.path.join('metadata', release['name'] + '.yml'))
		f.write(os.path.join('content_migrations', release['name'] + '.yml'))
	print
	print 'created tile', pivotal_file

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
