#!/usr/bin/env python

# tile-generator
#
# Copyright (c) 2015-Present Pivotal Software, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function
import os
import sys
import errno
import base64
import yaml
import json
from . import opsmgr
import random
import string
from . import build

from jinja2 import Environment, FileSystemLoader, exceptions, contextfilter

PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_PATH = os.path.realpath(os.path.join(PATH, '..', 'templates'))

def render_hyphens(input):
	return input.replace('_','-')

@contextfilter
def render_shell_string(context, input):
	expression = context.environment.compile_expression(input, undefined_to_none=False)
	return "'" + str(expression(context)).replace("'", "'\\''") + "'"

@contextfilter
def render_plans_json(context, input):
	name = 'missing.' + input
	form = context.environment.compile_expression(name, undefined_to_none=False)(context)
	plans = {}
	for p in form:
		plans[p['name']] = p
	return input.upper() + "='" + json.dumps(plans).replace("'", "'\\''") + "'"

TEMPLATE_ENVIRONMENT = Environment(
	trim_blocks=True, lstrip_blocks=True,
	comment_start_string='<%', comment_end_string='%>', # To completely ignore Ruby code blocks
)
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader(TEMPLATE_PATH)
TEMPLATE_ENVIRONMENT.filters['hyphens'] = render_hyphens
TEMPLATE_ENVIRONMENT.filters['shell_string'] = render_shell_string
TEMPLATE_ENVIRONMENT.filters['plans_json'] = render_plans_json

def render(errand_name, config_dir):
	template_file = os.path.join('jobs', errand_name + '.sh.erb')
	config = compile_config(config_dir)
	target_path = errand_name + '.sh'
	with open(target_path, 'wb') as target:
		target.write(TEMPLATE_ENVIRONMENT.get_template(template_file).render(config))
	return target_path

def mkdir_p(dir):
	try:
		os.makedirs(dir)
	except os.error as e:
		if e.errno != errno.EEXIST:
			raise

def get_file_properties(filename):
	try:
		with open(filename) as f:
			properties = yaml.safe_load(f)
			if properties is None:
				return {}
			else:
				return properties
	except IOError as e:
		print(filename, 'not found', file=sys.stderr)
		sys.exit(1)

def get_cf_properties():
	cf = opsmgr.get_cfinfo()
	properties = {}
	properties['cf'] = {
		'admin_user': cf['system_services_username'],
		'admin_password': cf['system_services_password'],
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
	context = get_file_properties(os.path.join(config_dir, 'tile.yml'))
	build.validate_config(context)
	build.add_defaults(context)
	build.upgrade_config(context)

	properties = {}
	missing = get_file_properties(os.path.join(config_dir, 'missing-properties.yml'))
	merge_properties(properties, get_cf_properties())
	merge_properties(properties, context)
	merge_property_array(properties, context.get('properties', []))
	for form in context.get('forms', []):
		merge_property_array(properties, form.get('properties', []))
	for package in context.get('packages', []):
		merge_properties(package, missing.get(package['name'], {}))
		merge_properties(package, properties['security'])
		merge_properties(properties, { package['name'].replace('-','_'): package })
	merge_properties(properties, missing)

	properties['org'] = properties.get('org', properties['name'] + '-org')
	properties['space'] = properties.get('space', properties['name'] + '-space')

	return {
		'context': context,
		'properties': properties,
		'missing': missing,
	}
