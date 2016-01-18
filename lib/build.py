#!/usr/bin/env python

import os
import shutil
import subprocess

PATH = os.path.dirname(os.path.realpath(__file__))
SABHA_PATH = os.path.realpath(os.path.join(PATH, '..', 'bosh-generic-sb-release', 'bin'))

def build(config):
	with cd('release', clobber=True):
		release = create_bosh_release(config)

def create_bosh_release(config):
	bosh('init', 'release')
	apps = config.get('apps', [])
	for app in apps:
		bash('addApp.sh', os.getcwd(), app['name'], 'true', 'true')

def bash(*argv):
	argv = list(argv)
	print ' '.join(argv)
	command = [ os.path.join(SABHA_PATH, argv[0]) ] + argv[1:]
	return subprocess.check_output(command, stderr=subprocess.STDOUT)

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
