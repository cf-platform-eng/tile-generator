#!/usr/bin/env python

import os
import sys
import errno
import base64

from jinja2 import Environment, FileSystemLoader, exceptions

PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_PATH = os.path.realpath(os.path.join(PATH, '..', 'templates'))

def render_base64(file):
	with open(os.path.realpath(os.path.join('..', file)), 'rb') as f:
		return base64.b64encode(f.read())

TEMPLATE_ENVIRONMENT = Environment(trim_blocks=True, lstrip_blocks=True)
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader(TEMPLATE_PATH)
TEMPLATE_ENVIRONMENT.globals['base64'] = render_base64

def render(target_path, template_file, config):
	target_dir = os.path.dirname(target_path)
	if target_dir != '':
		mkdir_p(target_dir)
	with open(target_path, 'wb') as target:
		target.write(TEMPLATE_ENVIRONMENT.get_template(template_file).render(config))

def exists(template_file):
	return os.exists(os.path.join(TEMPLATE_PATH, template_file))

def mkdir_p(dir):
   try:
      os.makedirs(dir)
   except os.error, e:
      if e.errno != errno.EEXIST:
         raise
