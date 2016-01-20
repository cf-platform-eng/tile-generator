#!/usr/bin/env python

import os
import sys
import shutil
import subprocess
import template
import urllib

PATH = os.path.dirname(os.path.realpath(__file__))
SABHA_PATH = os.path.realpath(os.path.join(PATH, '..', 'bosh-generic-sb-release', 'bin'))

VERBOSE=False

def build(config, verbose=False):
	context = config.copy()
	add_defaults(context)
	global VERBOSE
	VERBOSE = verbose
	with cd('release', clobber=True):
		create_bosh_release(context)
	with cd('product', clobber=True):
		create_tile(context)

def add_defaults(context):
	context['stemcell_criteria'] = context.get('stemcell_criteria', {})
	context['forms'] = context.get('forms', [])
	context['packages'] = context.get('packages', [])

def create_bosh_release(context):
	target = os.getcwd()
	bosh('init', 'release')
	template.render('src/templates/all_open.json', 'src/templates/all_open.json', context)
	template.render('config/final.yml', 'config/final.yml', context)
	bash('fetch_cf_cli.sh', target)
	pkgs = context.get('packages', [])
	for pkg in pkgs:
		jobs = pkg.get('jobs', [])
		cf_push = False
		cf_create_service_broker = False
		cf_create_buildpack = False
		for job in jobs:
			if job == 'cf-push':
				cf_push = True
			elif job == 'cf-create-service-broker':
				cf_create_service_broker = True
			elif job == 'cf-create-buildpack':
				cf_create_buildpack = True
			else:
				print >>sys.stderr, 'unknown job type', job, 'for', pkg.get('name', 'unnamed package')
				sys.exit(1)
		if cf_push or cf_create_service_broker:
			bash('addApp.sh', target, pkg['name'], str(cf_push).lower(), str(cf_create_service_broker).lower())
		if cf_create_buildpack:
			bash('addBuildpack.sh', target, pkg['name'])
		bash('addBlob.sh', target, os.path.join('..', pkg['path']), pkg['name'], pkg['name'])
#	add_cf_cli(context)
#	add_buildpacks(context)
#	add_service_brokers(context)
	output = bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', context['version'])
	context['release'] = bosh_extract(output, [
		{ 'label': 'name', 'pattern': 'Release name' },
		{ 'label': 'version', 'pattern': 'Release version' },
		{ 'label': 'manifest', 'pattern': 'Release manifest' },
		{ 'label': 'tarball', 'pattern': 'Release tarball' },
	])

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
#	with cd('releases'):
#		print 'tile generate release'
#		shutil.copy(release['tarball'], release['file'])
	print 'tile generate metadata'
	template.render('metadata/' + release['name'] + '.yml', 'tile/metadata.yml', context)
#	with cd('content_migrations'):
#		print 'tile generate content-migrations'
#		migrations = tile_migrations(context, release)
#		with open(release['name'] + '.yml', 'wb') as f:
#			write_yaml(f, migrations)
#	pivotal_file = release['name'] + '-' + release['version'] + '.pivotal'
#	with zipfile.ZipFile(pivotal_file, 'w') as f:
#		f.write(os.path.join('releases', release['file']))
#		f.write(os.path.join('metadata', release['name'] + '.yml'))
#		f.write(os.path.join('content_migrations', release['name'] + '.yml'))
#	print
#	print 'created tile', pivotal_file

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
        if os.path.isdir(self.newPath):
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
