#!/usr/bin/env python

import os
import sys
import shutil
import subprocess
import template

PATH = os.path.dirname(os.path.realpath(__file__))
SABHA_PATH = os.path.realpath(os.path.join(PATH, '..', 'bosh-generic-sb-release', 'bin'))

VERBOSE=False

def build(config, verbose=False):
	global VERBOSE
	VERBOSE = verbose
	with cd('release', clobber=True):
		create_bosh_release(config)
	with cd('product', clobber=True):
		create_tile(config)

def create_bosh_release(config):
	target = os.getcwd()
	bosh('init', 'release')
	template.render('src/templates/all_open.json', 'all_open.json', config)
	template.render('config/final.yml', 'bosh-final.yml', config)
	bash('fetch_cf_cli.sh', target)
	apps = config.get('apps', [])
	for app in apps:
		bash('addApp.sh', target, app['name'], 'true', 'false')
		bash('addBlob.sh', target, os.path.join('..', app['path']), app['name'], app['name'])
	brokers = config.get('brokers', [])
	for broker in brokers:
		bash('addApp.sh', target, broker['name'], 'true', 'true')
		bash('addBlob.sh', target, os.path.join('..', broker['path']), broker['name'], broker['name'])
	buildpacks = config.get('buildpacks', [])
	for bp in buildpacks:
		bash('addBuildpack.sh', target, bp['name'])
		bash('addBlob.sh', target, os.path.join('..', bp['path']), bp['name'], bp['name'])
	blobs = config.get('blobs', [])
	for blob in blobs:
		bash('addBlob.sh', target, os.path.join('..', blob['path']), blob['name'])
#	add_cf_cli(config)
#	add_buildpacks(config)
#	add_service_brokers(config)
	output = bosh('create', 'release', '--force', '--final', '--with-tarball', '--version', config['version'])
	config['release'] = bosh_extract(output, [
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

def create_tile(config):
	release = config['release']
	release['file'] = os.path.basename(release['tarball'])
#	with cd('releases'):
#		print 'tile generate release'
#		shutil.copy(release['tarball'], release['file'])
	with cd('metadata'):
		print 'tile generate metadata'
		template.render('metadata/' + release['name'] + '.yml', 'tile-metadata.yml', config)
#	with cd('content_migrations'):
#		print 'tile generate content-migrations'
#		migrations = tile_migrations(config, release)
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

def add_blob(name, binary, url=None, commands=None):
	bosh('generate', 'package', name)
	srcdir = os.path.join('src', name)
	pkgdir = os.path.join('packages', name)
	mkdir_p(srcdir)
	if url is None:
		shutil.copy(os.path.join('..', binary), srcdir)
	else:
		urllib.urlretrieve(url, os.path.join(srcdir, binary))
	spec = {
		'name': name,
		'dependencies': [],
		'files': [ name + '/*' ],
	}
	with cd(pkgdir):
		with open('packaging', 'wb') as f:
			if commands is None:
				f.write('cp ' + name + '/* ${BOSH_INSTALL_TARGET}')
			else:
				for c in commands:
					f.write(c + '\n')
		with open('pre_packaging', 'wb') as f:
			pass
		with open('spec', 'wb') as f:
			write_yaml(f, spec)


def add_cf_cli():
	add_src_package(
		'cf_cli',
		'cf-linux-amd64.tgz',
		url='https://cli.run.pivotal.io/stable?release=linux64-binary&source=github-rel',
		commands=[
			'set -e -x',
			'mkdir -p ${BOSH_INSTALL_TARGET}/bin',
			'cd cf_cli',
			'tar zxvf cf-linux-amd64.tgz',
			'cp cf ${BOSH_INSTALL_TARGET}/bin/'
		]
	)

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

def update_version(config, version):
	if version is None:
		version = 'patch'
	prior_version = config.get('version', None)
	if prior_version is not None:
		config['history'] = config.get('history', [])
		config['history'] += [ prior_version ]
	if not is_semver(version):
		semver = config.get('version', '0.0.0')
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
	config['version'] = version
	print 'version:', version

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
