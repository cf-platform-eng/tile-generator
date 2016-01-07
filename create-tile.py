#!/usr/bin/env python

import os
import errno
import subprocess
import sys
import yaml
import shutil
import urllib

CONFIG_FILE = "tile.yml"

def main(argv):
	config = read_config()
	update_version(config)
	with cd('release'):
		create_bosh_release(config)

def create_bosh_release(config):
	bosh('init', 'release')
	add_bosh_config(config)
	add_cf_cli()
	add_buildpacks(config)
	add_service_brokers(config)
	bosh('create', 'release', '--final', '--with-tarball')

def add_bosh_config(config):
	spec = {
		'blobstore': {
			'provider': 'local',
			'options': {
				'blobstore_path': '/tmp/unused-blobs'
			}
		},
		'final_name': config['name']
	}
	with cd('config'):
		with open('final.yml', 'wb') as f:
			f.write(yaml.safe_dump(spec))

def add_buildpacks(config):
	buildpacks = config.get('buildpacks', [])
	for bp in buildpacks:
		validate_buildpack(bp)
		add_src_package(bp['name'], bp['binary'])
		add_bosh_job('install_' + bp['name'], [
				'cf api https://api.' +
					bosh_property('cf.domain') +
					bosh_property_if('ssl.skip_cert_verify', ' --skip-ssl-validation'),
				'cf auth ' +
					bosh_property('cf.admin_user') + ' ' +
					bosh_property('cf.admin_password'),
				'cf delete-buildpack ' + 
					bp['name'] + ' -f',
				'cf create-buildpack ' +
					bp['name'] + ' ${PACKAGE_PATH}/' + bp['name'] + '/* ' +
					bosh_property(bp['name'] + '_rank') +
					' --enable',
			],
			properties = {
				bp['name'] + '_rank': {
					'description': 'The relative ranking of ' + bp['name'],
					'default': bp['rank'],
				}
			},
			dependencies = [ bp['name'] ])
		add_bosh_job('remove_' + bp['name'], [
				'cf api https://api.' +
					bosh_property('cf.domain') +
					bosh_property_if('ssl.skip_cert_verify', ' --skip-ssl-validation'),
				'cf auth ' +
					bosh_property('cf.admin_user') + ' ' +
					bosh_property('cf.admin_password'),
				'cf delete-buildpack ' + 
					bp['name'] + ' -f',
			],
			dependencies = [ bp['name'] ])

def validate_buildpack(bp):
	bp['name']   = bp.get('name', None)
	bp['binary'] = bp.get('binary', None)
	bp['rank']   = bp.get('rank', '0')
	if bp['name'] is None or bp['binary'] is None:
		print >> sys.stderr, 'Each buildpack entry must specify a name, a binary, and optionally a default rank'
		sys.exit(1)
	if len(bp['name']) > 20 or not bp['name'].endswith('_buildpack'):
		print >> sys.stderr, bp['name'], '- Buildpack names are by convention short and end with _buildpack'
		sys.exit(1)

def bosh_property(key):
	return '<%= properties.' + key + ' %>'

def bosh_property_if(key, body):
	return '<% if properties.' + key + ' %>' + body + '<% end %>'

def add_bosh_job(name, commands, properties={}, dependencies=[]):
	commands = [
			'#!/bin/bash',
			'set -e -x',
			'export PATH="/var/vcap/packages/cf_cli/bin:$PATH"',
			'export CF_HOME=`pwd`/home/cf',
			'mkdir -p $CF_HOME',
		] + commands
	bosh('generate', 'job', name)
	shname = name + '.sh.erb'
	spec = {
		'name': name,
		'templates': { shname: 'bin/run' },
		'packages': [ 'cf_cli' ] + dependencies,
		'properties' : {
			'ssl.skip_cert_verify': { 'description': 'Whether to verify SSL certs when making web requests' },
			'cf.domain': { 'Cloud Foundry system domain' },
			'cf.admin_user': { 'Username of the CF admin user' },
			'cf.admin_password': { 'Password for the CF admin user' },
		}
	}
	spec['properties'].update(properties)
	jobdir = os.path.join('jobs', name)
	with cd(jobdir):
		with open('monit', 'wb') as f:
			pass
		with open('spec', 'wb') as f:
			f.write(yaml.safe_dump(spec))
		with cd('templates'):
			with open(shname, 'wb') as f:
				for c in commands:
					f.write(c + '\n')

def add_src_package(name, binary, url=None):
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
			f.write('cp ' + name + '/* ${BOSH_INSTALL_TARGET}')
		with open('pre_packaging', 'wb') as f:
			pass
		with open('spec', 'wb') as f:
			f.write(yaml.safe_dump(spec))

def add_service_brokers(config):
	brokers = config.get('service-brokers', None)
	if brokers is None:
		return
	print >> sys.stderr, 'Service broker support is not yet implemented'
	sys.exit(1)

def add_cf_cli():
	add_src_package('cf_cli', 'cf-linux-amd64.tgz', url='https://cli.run.pivotal.io/stable?release=linux64-binary&source=github-rel')

def read_config():
	try:
		with open(CONFIG_FILE) as config_file:
			return yaml.load(config_file)
	except IOError as e:
		print >> sys.stderr, "File tile.yml not found. Must execute in the root directory of your tile."
		sys.exit(1)

def update_version(config):
	version = config.get('version', '0.0.1')
	if os.path.isdir('product'):
		semver = version.split('.')
		if len(semver) != 3:
			print >>sys.stderr, "Version must be in semver format (x.x.x)"
		semver[2] = str(int(semver[2]) + 1)
		config['version'] = '.'.join(semver)

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

class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
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

if __name__ == "__main__":
	main(sys.argv)