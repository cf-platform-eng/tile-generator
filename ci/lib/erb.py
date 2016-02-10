#!/usr/bin/env python

import os
import sys
import errno
import base64

from jinja2 import Environment, FileSystemLoader, exceptions

PATH = os.path.dirname(os.path.realpath(__file__))

TEMPLATE_ENVIRONMENT = Environment(variable_start_string='<%=', variable_end_string='%>')
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader('.')

def render(target_path, template_file, config):
	target_dir = os.path.dirname(target_path)
	if target_dir != '':
		mkdir_p(target_dir)
	with open(target_path, 'wb') as target:
		target.write(TEMPLATE_ENVIRONMENT.get_template(template_file).render(config))

def mkdir_p(dir):
   try:
      os.makedirs(dir)
   except os.error, e:
      if e.errno != errno.EEXIST:
         raise
