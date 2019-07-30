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


import os
import re
import sys
import errno
import yaml

from jinja2 import Template, Environment, FileSystemLoader, exceptions, contextfilter

PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATE_PATH = os.path.realpath(os.path.join(PATH, 'templates'))

PROPERTY_FIELDS = {
	'simple_credentials': ['identity', 'password'],
	'rsa_cert_credentials': [ 'private_key_pem', 'cert_pem', 'public_key_pem', 'cert_and_private_key_pems' ],
	'rsa_pkey_credentials': [ 'private_key_pem', 'public_key_pem', 'public_key_openssh', 'public_key_fingerprint' ],
	'salted_credentials': [ 'salt', 'identity', 'password' ],
	'selector': [ 'value', ('selected_option', 'selected_option.parsed_manifest(manifest_snippet)') ],
}

def render_hyphens(input):
	return input.replace('_','-')

def expand_selector(input):
	if input.get('type', None) == 'selector':
		for option in input.get('option_templates', []):
			properties = ''
			for p in option.get('property_blueprints', []):
				if p['type'] in PROPERTY_FIELDS:
					properties += p['name'] + ': { '
					subproperties = []
					for subproperty in PROPERTY_FIELDS[p['type']]:
						if type(subproperty) is tuple:
							subproperties.append('{}: (( .properties.{}.{}.{}.{} ))'.format(subproperty[0], input['name'], option['name'], p['name'], subproperty[1]))
						else:
							subproperties.append('{}: (( .properties.{}.{}.{}.{} ))'.format(subproperty, input['name'], option['name'], p['name'], subproperty))
					properties += ', '.join(subproperties) + ' }\r\n'
				else:
					properties += p['name'] + ': (( .properties.' + input['name'] + '.' + option['name'] + '.' + p['name'] + '.value ))\r\n'
			option['named_manifests'] = option.get("named_manifests", [])
			option['named_manifests'].append({
				'name': 'manifest_snippet',
				'manifest': properties
			})
	return input



def render_yaml(input):
	# Inspired by https://stackoverflow.com/questions/50519454/python-yaml-dump-using-block-style-without-quotes
	def multiline_representer(dumper, data):
		return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|" if "\n" in data else None)
	yaml.SafeDumper.add_representer(str, multiline_representer)
	yaml.SafeDumper.ignore_aliases = lambda *args : True
	return yaml.safe_dump(input, default_flow_style=False, width=float("inf"))

def render_yaml_literal(input):
	return yaml.safe_dump(input, default_flow_style=False, default_style='|', width=float("inf"))

def render_shell_string(input):
	return '<%= Shellwords.escape ' + input + ' %>'

def render_plans_json(input, escape=True, export=True):
	property_name = input['name']
	variable_name = input.get('variable_name', property_name.upper())
	value = '=<%= Shellwords.escape JSON.dump(plans) %>' if escape else '=<%= JSON.dump(plans) %>'
	export = 'export ' if export else ''
	return ('<%\n'
	'	plans = { }\n'
	'	p("' + property_name + '").each do |plan|\n'
	'		plan_name = plan[\'name\']\n'
	'		plans[plan_name] = plan\n'
	'	end\n'
	'%>\n'
	'' + export + variable_name + value)

def render_selector_json(input, escape=True, export=True):
	value = '=<%= Shellwords.escape JSON.dump(hash) %>' if escape else '=<%= JSON.dump(hash) %>'
	export = 'export ' if export else ''
	return ('<%\n'
	'	hash = { }\n'
	'	hash["value"] = p("' + input + '")["value"]\n'
	'	hash["selected_option"] = { }\n'
	'	if p("' + input + '")["selected_option"]\n'
	'		p("' + input + '")["selected_option"].each_pair do |key, value|\n'
	'			hash["selected_option"][key] = value\n'
	'		end\n'
	'	end\n'
	'%>\n'
	'' + export + input.upper() + value)

def render_collection_json(input, escape=True, export=True):
	value = '=<%= Shellwords.escape JSON.dump(array) %>' if escape else '=<%= JSON.dump(array) %>'
	export = 'export ' if export else ''
	return ('<%\n'
	'	array = [ ]\n'
	'	p("' + input + '").each do |m|\n'
	'		member = { }\n'
	'		m.each_pair do |key, value|\n'
	'			member[key] = value\n'
	'		end\n'
	'		array << member\n'
	'	end\n'
	'%>\n'
	'' + export + input.upper() + value)

def render_property_json(input, escape=True, export=True):
	escape = ' Shellwords.escape' if escape else ''
	export = 'export ' if export else ''
	return(export + '{}=<%={} properties.{}.marshal_dump.to_json %>'.format(input.upper(), escape, input))

def render_property_value(input, escape=True, export=True):
	escape = ' Shellwords.escape' if escape else ''
	export = 'export ' if export else ''
	return(export + '{}=<%={} properties.{} %>'.format(input.upper(), escape, input))

def render_env_variable(property, escape=True, export=True):
	complex_types = (
		'simple_credentials',
		'rsa_cert_credentials',
		'rsa_pkey_credentials',
		'salted_credentials',
		'selector',
	)
	if property['type'] in [ 'selector' ]:
		return render_selector_json(property['name'], escape, export)
	elif property['type'] in [ 'collection' ]:
		return render_collection_json(property['name'], escape, export)
	elif property['type'] in complex_types:
		return render_property_json(property['name'], escape, export)
	else:
		return render_property_value(property['name'], escape, export)

def render_property(property):
	"""Render a property for bosh manifest, according to its type."""
	# This ain't the prettiest thing, but it should get the job done.
	# I don't think we have anything more elegant available at bosh-manifest-generation time.
	# See https://docs.pivotal.io/partners/product-template-reference.html for list.
	if 'type' in property and property['type'] in PROPERTY_FIELDS:
		fields = {}
		for field in PROPERTY_FIELDS[property['type']]:
			if type(field) is tuple:
				fields[field[0]] = '(( .properties.{}.{} ))'.format(property['name'], field[1])
			else:
				fields[field] = '(( .properties.{}.{} ))'.format(property['name'], field)
		out = { property['name']: fields }
	else:
		if property.get('is_reference', False):
			out = { property['name']: property['default'] }
		else:
			out = { property['name']: '(( .properties.{}.value ))'.format(property['name']) }
	return out

def render_shell_variable_name(s):
        """Convert s to a shell variable identifier."""
        return re.sub(r'[^a-zA-Z0-9]+', '_', s).upper()

@contextfilter
def render(context, input):
	template = Template(input)
	return template.render(context)

TEMPLATE_ENVIRONMENT = Environment(trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.do'])
TEMPLATE_ENVIRONMENT.loader = FileSystemLoader(TEMPLATE_PATH)
TEMPLATE_ENVIRONMENT.filters['hyphens'] = render_hyphens
TEMPLATE_ENVIRONMENT.filters['expand_selector'] = expand_selector
TEMPLATE_ENVIRONMENT.filters['yaml'] = render_yaml
TEMPLATE_ENVIRONMENT.filters['yaml_literal'] = render_yaml_literal
TEMPLATE_ENVIRONMENT.filters['shell_string'] = render_shell_string
TEMPLATE_ENVIRONMENT.filters['shell_variable_name'] = render_shell_variable_name
TEMPLATE_ENVIRONMENT.filters['plans_json'] = render_plans_json
TEMPLATE_ENVIRONMENT.filters['property'] = render_property
TEMPLATE_ENVIRONMENT.filters['env_variable'] = render_env_variable
TEMPLATE_ENVIRONMENT.filters['render'] = render

def render(target_path, template_file, config):
	target_dir = os.path.dirname(target_path)
	if target_dir != '':
		mkdir_p(target_dir)
	with open(target_path, 'wb') as target:
		target.write(bytes(TEMPLATE_ENVIRONMENT.get_template(template_file).render(config), 'utf-8'))

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
