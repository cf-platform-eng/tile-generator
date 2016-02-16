#!/usr/bin/env python

import os
import sys
import errno
import base64
import yaml
import json
import opsmgr
import random
import string

from jinja2 import Environment, FileSystemLoader, exceptions

PATH = os.path.dirname(os.path.realpath(__file__))

TEMPLATE_ENVIRONMENT = Environment(
	variable_start_string='<%=', variable_end_string='%>',
	comment_start_string='<%', comment_end_string='%>', # To completely ignore Ruby code blocks
)
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader('.')

def render(target_path, template_file, config_dir):
	config = compile_config(config_dir)
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

def get_file_properties(filename):
	try:
		with open(filename) as f:
			return yaml.safe_load(f)
	except IOError as e:
		print >> sys.stderr, filename, 'not found'
		sys.exit(1)

def get_cf_properties():
	cf = opsmgr.get_cfinfo()
	properties = {}
	properties['cf'] = {
		'admin_user': cf['admin_username'],
		'admin_password': cf['admin_password'],
	}
	properties['domain'] = cf['system_domain']
	properties['app_domains'] = [ cf['apps_domain'] ]
	properties['ssl'] = { 'skip_cert_verify': True }
	properties['security'] = {
		'user': 'admin',
		'password': ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(12))
	}
	return properties

def merge_properties(properties, new_properties):
	for p in new_properties:
		if properties.get(p, None) is None:
			properties[p] = new_properties[p]

def merge_property_array(properties, new_properties):
	for p in new_properties:
		name = p['name']
		if properties.get(name, None) is None:
			value = p.get('value', p.get('default', None))
			if value is not None:
				properties[name] = value

def compile_config(config_dir):
	properties = {}
	config1 = get_file_properties(os.path.join(config_dir, 'tile.yml'))
	config2 = get_file_properties(os.path.join(config_dir, 'missing-properties.yml'))
	merge_properties(properties, get_cf_properties())
	merge_properties(properties, config1)
	merge_property_array(properties, config1.get('properties', []))
	for form in config1.get('forms', []):
		merge_property_array(properties, form.get('properties', []))
	for package in config1.get('packages', []):
		merge_properties(package, config2.get(package['name'], {}))
		merge_properties(package, properties['security'])
		merge_properties(properties, { package['name']: package })
	merge_properties(properties, config2)
	return {
		'properties': properties,
		'JSON': { 'dump': json.dumps },
		'plans': properties.get('dynamic_service_plans', {})
	}
