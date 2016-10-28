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

from jinja2 import Template, Environment, FileSystemLoader, exceptions, contextfilter

PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_PATH = os.path.realpath(os.path.join(PATH, 'templates'))

def render_base64(file):
	try:
		with open(os.path.realpath(file), 'rb') as f:
			return base64.b64encode(f.read())
	except Exception as e:
		print(e, file=sys.stderr)
		sys.exit(1)

def render_hyphens(input):
	return input.replace('_','-')

def render_yaml(input):
	return yaml.safe_dump(input, default_flow_style=False)

def render_shell_string(input):
	return '<%= Shellwords.escape ' + input + ' %>'

def render_plans_json(input):
	return ('<%\n'
	'	plans = { }\n'
	'	p("' + input + '").each do |plan|\n'
	'		plan_name = plan[\'name\']\n'
	'		plans[plan_name] = plan\n'
	'	end\n'
	'%>\n'
	'' + input.upper() + '=<%= Shellwords.escape JSON.dump(plans) %>')

def render_property_value(property):
	complex_types = (
		'simple_credentials',
		'rsa_cert_credentials',
		'rsa_pkey_credentials',
		'salted_credentials',
		'selector',
	)
	if property['type'] in complex_types:
		return 'properties.{}.marshal_dump.to_json'.format(property['name'])
	else:
		return 'properties.' + property['name']

def render_property(property):
	"""Render a property for bosh manifest, according to its type."""
	# This ain't the prettiest thing, but it should get the job done.
	# I don't think we have anything more elegant available at bosh-manifest-generation time.
	# See https://docs.pivotal.io/partners/product-template-reference.html for list
	property_fields = {
		'simple_credentials': ['identity', 'password'],
		'rsa_cert_credentials': [ 'private_key_pem', 'cert_pem', 'public_key_pem', 'cert_and_private_key_pems' ],
		'rsa_pkey_credentials': [ 'private_key_pem', 'public_key_pem', 'public_key_openssh', 'public_key_fingerprint' ],
		'salted_credentials': [ 'salt', 'identity', 'password' ],
		'selector': [ 'value', 'selected_option', 'nested context' ],
	}
	if 'type' in property and property['type'] in property_fields:
		fields = {}
		for field in property_fields[property['type']]:
			fields[field] = '(( .properties.{}.{} ))'.format(property['name'], field)
		out = { property['name']: fields }
	else:
		# Other types use 'value'.
		out = { property['name']: '(( .properties.{}.value ))'.format(property['name']) }
	return out

@contextfilter
def render(context, input):
	template = Template(input)
	return template.render(context)

TEMPLATE_ENVIRONMENT = Environment(trim_blocks=True, lstrip_blocks=True)
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader(TEMPLATE_PATH)
TEMPLATE_ENVIRONMENT.globals['base64'] = render_base64
TEMPLATE_ENVIRONMENT.filters['hyphens'] = render_hyphens
TEMPLATE_ENVIRONMENT.filters['yaml'] = render_yaml
TEMPLATE_ENVIRONMENT.filters['shell_string'] = render_shell_string
TEMPLATE_ENVIRONMENT.filters['plans_json'] = render_plans_json
TEMPLATE_ENVIRONMENT.filters['property'] = render_property
TEMPLATE_ENVIRONMENT.filters['property_value'] = render_property_value
TEMPLATE_ENVIRONMENT.filters['render'] = render

def render(target_path, template_file, config):
	target_dir = os.path.dirname(target_path)
	if target_dir != '':
		mkdir_p(target_dir)
	with open(target_path, 'wb') as target:
		target.write(TEMPLATE_ENVIRONMENT.get_template(template_file).render(config))

def exists(template_file):
	return os.exists(path(template_file))

def path(template_file):
	return os.path.join(TEMPLATE_PATH, template_file)

def mkdir_p(dir):
	try:
		os.makedirs(dir)
	except os.error as e:
		if e.errno != errno.EEXIST:
			raise
