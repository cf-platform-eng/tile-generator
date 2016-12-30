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
import sys
import yaml
import json
import requests
import time
try:
	# Python 3
	from urllib.parse import urlparse
except ImportError:
	# Python 2
	from urlparse import urlparse
import subprocess
import pty
import os
import select
import glob

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def find_credentials(target):
	if not target.endswith('.yml'):
		target += '.yml'
	if '/' in target:
		return target
	dir = get_credential_dir(update=True)
	return os.path.join(dir, target)

def find_credential_dir():
	dirname = 'pie-credentials'
	parent = '.'
	while not os.path.samefile(parent, '/'):
		candidate = os.path.join(parent, dirname)
		if os.path.exists(candidate):
			return candidate
		pattern = os.path.join(parent, '*', dirname)
		matches = glob.glob(pattern)
		if len(matches) > 0:
			return matches[0]
		parent = os.path.join('..', parent)

def get_credential_dir(update=False):
	dir = find_credential_dir()
	if update:
		devnull = open(os.devnull,"w")
		subprocess.call(['git', 'pull'], cwd=dir, stdout=devnull, stderr=devnull)
	return dir

def get_credentials(target=None):
	if target is not None:
		get_credentials.credential_file = find_credentials(target)
	credential_file = get_credentials.credential_file
	try:
		with open(credential_file) as cred_file:
			creds = yaml.safe_load(cred_file)
			creds['opsmgr']
			creds['opsmgr']['url']
			creds['opsmgr']['username']
			creds['opsmgr']['password']
	except KeyError as e:
		print('Credential file is missing a value:', e.message, file=sys.stderr)
		sys.exit(1)
	except IOError as e:
		print('Credential file "' + credential_file + '" not found', file=sys.stderr)
		sys.exit(1)
	return creds

# This default handles the case where we are executing from within a
# concourse pool-resource repository, where the claimed PCF instance
# metadata is available in a file named './metadata'
#
get_credentials.credential_file = 'metadata'

class auth(requests.auth.AuthBase):

	def __init__(self, creds):
		self.creds = creds

	def __call__(self, request):
		url = self.creds.get('opsmgr').get('url') + '/uaa/oauth/token'
		username = self.creds.get('opsmgr').get('username')
		password = self.creds.get('opsmgr').get('password')
		headers = { 'Accept': 'application/json' }
		data = {
			'grant_type': 'password',
			'client_id': 'opsman',
			'client_secret': '',
			'username': username,
			'password': password,
			'response_type': 'token',
		}
		response = requests.post(url, data=data, verify=False, headers=headers)
		if response.status_code != requests.codes.ok:
			return requests.auth.HTTPBasicAuth(username, password)(request)
		response = response.json()
		access_token = response.get('access_token')
		token_type = response.get('token_type')
		request.headers['Authorization'] = token_type + ' ' + access_token
		return request

def get(url, stream=False, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	headers = { 'Accept': 'application/json' }
	response = requests.get(url, auth=auth(creds), verify=False, headers=headers, stream=stream)
	check_response(response, check=check)
	return response

def put(url, payload, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	response = requests.put(url, auth=auth(creds), verify=False, data=payload)
	check_response(response, check=check)
	return response

def put_json(url, payload):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	response = requests.put(url, auth=auth(creds), verify=False, json=payload)
	check_response(response)
	return response

def post(url, payload, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	response = requests.post(url, auth=auth(creds), verify=False, data=payload)
	check_response(response, check)
	return response

def post_yaml(url, filename, payload):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	files = { filename: yaml.safe_dump(payload) }
	response = requests.post(url, auth=auth(creds), verify=False, files=files)
	check_response(response)
	return response

def upload(url, filename, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	files = { 'product[file]': open(filename, 'rb') }
	response = requests.post(url, auth=auth(creds), verify=False, files=files)
	if response.status_code == 422:
		errors = response.json()["errors"]
		product = errors.get('product', [])
		for reason in product:
			if reason.startswith('Metadata already exists for'):
				print('-','version already uploaded')
				return response
	check_response(response, check)
	return response

def delete(url, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	response = requests.delete(url, auth=auth(creds), verify=False)
	check_response(response, check=check)
	return response

def check_response(response, check=True):
	if check and response.status_code != requests.codes.ok:
		print('-', response.status_code, response.request.url, file=sys.stderr)
		try:
			errors = response.json()["errors"]
			print('- '+('\n- '.join(json.dumps(errors, indent=4).splitlines())), file=sys.stderr)
		except:
			print(response.text, file=sys.stderr)
		sys.exit(1)

def ssh(commands = [], working_dir='/var/tempest/workspaces/default', silent=False, debug=False):
	interactive = len(commands) == 0
	creds = get_credentials()
	url = creds.get('opsmgr').get('url')
	host = urlparse(url).hostname
	command = [
		'ssh',
		'-q',
		'-o', 'UserKnownHostsFile=/dev/null',
		'-o', 'StrictHostKeyChecking=no',
		'ubuntu@' + host
	]
	prompt = host.split('.',1)[0] + '$ '
	bootstrap = 'cd ' + working_dir + '; '
	bootstrap += 'stty -echo; '
	bootstrap += 'export PS1="' + prompt + '"\n'
	pid, tty = pty.fork()
	if pid == 0:
		try:
			subprocess.check_call(command)
			sys.exit(0)
		except subprocess.CalledProcessError as error:
			print('Command failed with exit code', error.returncode)
			print(error.output)
			sys.exit(error.returncode)
	else:
		ssh_process_output(tty, '*password:', show_output=False, show_prompt=False, debug=debug) # Wait for the password prompt (and eat it)
		os.write(tty, creds.get('opsmgr').get('password') + '\n') # Send the password
		ssh_process_output(tty, '*$ ', show_output=False, show_prompt=False, debug=debug) # Wait for first shell prompt (and eat it)
		os.write(tty, bootstrap) # Send the bootstrap sequence
		ssh_process_output(tty, prompt, show_output=False, show_prompt=interactive, debug=debug) # Eat until prompt
		if interactive:
			ssh_interactive(tty)
		else:
			try:
				while len(commands) > 0:
					if debug:
						print(commands[0])
					os.write(tty, commands[0] + '\n')
					commands = commands[1:]
					ssh_process_output(tty, prompt, show_output=not silent, show_prompt=False)
				os.write(tty, 'exit\n')
				ssh_process_output(tty, prompt, show_output=False, show_prompt=False)
			except:
				# To allow 'exit' or 'reboot', the last command is allowed to close the connection and cause an I/O failure
				if len(commands) > 0:
					raise

def ssh_interactive(tty):
	while True:
		rlist, wlist, xlist = select.select([sys.stdin.fileno(), tty], [], [])
		if sys.stdin.fileno() in rlist:
			input = os.read(sys.stdin.fileno(), 1024)
			if len(input) == 0:
				break
			else:
				os.write(tty, input)
				os.fsync(tty)
		elif tty in rlist:
			output = os.read(tty, 1024)
			if len(output) == 0:
				break
			sys.stdout.write(output)
			sys.stdout.flush()
	os.close(tty)

def ssh_process_output(tty, prompt, show_output=True, show_prompt=True, debug=False):
	if debug:
		print('?', prompt)
	prior = ''
	eating = True
	while eating:
		if debug:
			sys.stdout.write('<')
			sys.stdout.flush()
		output = os.read(tty, 1024)
		if len(output) == 0:
			return
		output = prior + output
		lines = output.splitlines(True)
		for line in lines:
			if ssh_match(prompt, line):
				eating = False
				if show_prompt or debug:
					if debug:
						sys.stdout.write('=')
						sys.stdout.flush()
					sys.stdout.write(line)
					sys.stdout.flush()
					if debug:
						sys.stdout.write('\n')
						sys.stdout.flush()
			elif (show_output or debug) and line.endswith('\n'):
				if debug:
					sys.stdout.write('>')
					sys.stdout.flush()
				sys.stdout.write(line)
				sys.stdout.flush()
		lastline = lines[-1]
		if eating and not lastline.endswith('\n'):
			if debug:
				sys.stdout.write('/')
				sys.stdout.flush()
				sys.stdout.write(lastline)
				sys.stdout.flush()
				sys.stdout.write('\n')
				sys.stdout.flush()
			prior = lastline
		else:
			prior = ''

def ssh_match(pattern, line):
	if pattern.startswith('*'):
		return pattern[1:] in line
	else:
		return line.startswith(pattern)

def get_products():
	available_products = get('/api/products').json()
	installed_products = get('/api/installation_settings').json()['products']
	for product in available_products:
		installed = [ p for p in installed_products if p['identifier'] == product['name'] and p['product_version'] == product['product_version'] ]
		product['installed'] = len(installed) > 0
		if product['installed']:
			product['guid'] = installed[0]['guid']
	return available_products

def get_version():
	# 1.7 and 1.8 have version in the diagnostic report.
	response = get('/api/v0/diagnostic_report', check=False)
	if response.status_code == requests.codes.ok:
		diag = response.json()
		version = diag['versions']['release_version']
		return [ int(x) for x in version.split('.') ]
	# 1.6 (and maybe earlier?) has the version in the p-bosh (Ops Manager Director) product.
	products = get('/api/products').json()
	for product in products:
		if product['name'] == 'p-bosh':
			version = product['product_version']
			return [ int(x) for x in version.split('.') ]
	print('Error: could not determine Ops Manager version.', file=sys.stderr)
	sys.exit(1)

def get_job_guid(job_identifier, jobs_settings):
	for job in jobs_settings:
		if job.get('identifier', None) == job_identifier:
			return job['guid']
	print('Could not find job with identifier', job_identifier, file=sys.stderr)
	sys.exit(1)

def configure(product, properties, strict=False, skip_validation=False):
	settings = get('/api/installation_settings').json()
	infrastructure = settings['infrastructure']
	product_settings = [ p for p in settings['products'] if p['identifier'] == product ]
	if len(product_settings) < 1:
		print('Product', product, 'does not appear to be installed', file=sys.stderr)
		sys.exit(1)
	product_settings = product_settings[0]
	properties = properties if properties is not None else {}
	#
	# Make sure Elastic Runtime tile is installed
	#
	cf = [ p for p in settings['products'] if p['identifier'] == 'cf' ]
	if len(cf) < 1:
		print('Required product Elastic Runtime is missing', file=sys.stderr)
		sys.exit(1)
	#
	# Use the Elastic Runtime stemcell (unless the --strict option was used)
	#
	if not strict:
		stemcell = cf[0]['stemcell']
		print('- Using stemcell', stemcell['name'], 'version', stemcell['version'])
		product_settings['stemcell'] = stemcell
		post_yaml('/api/installation_settings', 'installation[file]', settings)
	#
	# Use the first availability zone
	#
	product_settings['availability_zone_references'] = [ az['guid'] for az in infrastructure['availability_zones'] ]
	product_settings['singleton_availability_zone_reference'] = infrastructure['availability_zones'][0]['guid']
	#
	# Insert supplied properties
	#
	jobs_properties = properties.pop('jobs', {})
	missing_properties = []
	for job in product_settings.get('jobs', []):
		job_properties = jobs_properties.get(job['identifier'], {})
		for job_property in job.get('properties', []):
			property_name = job_property['identifier']
			if property_name == 'app_credentials':
				# app_credentials are generated in opsmgr; skip.
				continue
			if property_name in job_properties:
				job_property['value'] = job_properties[property_name]
			else:
				if job_property.get('value', None) is None:
					missing_properties.append('.'.join(('jobs', job['identifier'], property_name)))
	for p in product_settings.get('properties', []):
		key = p['identifier']
		value = properties.get(key, None)
		if value is not None:
			p['value'] = value
		else:
			if p.get('value', None) is None:
				missing_properties += [ key ]
	if not skip_validation and len(missing_properties) > 0:
		print('Input file is missing required properties:', file=sys.stderr)
		print('- ' + '\n- '.join(missing_properties), file=sys.stderr)
		sys.exit(1)
	#
	# Normalize az properties
	#
	for az in infrastructure['availability_zones']:
		if az.get('name', None) is None:
			az['name'] = az['iaas_identifier']
	#
	# Update using the appropriate API for the Ops Manager version
	#
	version = get_version()
	if version[0] == 1 and version[1] >= 8:
		networks_and_azs = {
			'networks_and_azs': {
				'singleton_availability_zone': { 'name': infrastructure['availability_zones'][0]['name'] },
				'other_availability_zones': [ { 'name': az['name'] } for az in infrastructure['availability_zones'] ],
				'network': { 'name': infrastructure['networks'][0]['name'] },
			}
		}
		scoped_properties = {}
		resource_config = {}
		for job, job_properties in jobs_properties.items():
			if 'resource_config' in job_properties:
				job_resource_config = job_properties.pop('resource_config')
				job_guid = get_job_guid(job, product_settings.get('jobs', []))
				resource_config[job_guid] = job_resource_config
			for name, value in job_properties.items():
				key = '.'.join(('', job, name))
				scoped_properties[key] = value
		for key in properties:
			value = properties[key]
			if not key.startswith('.'):
				key = '.properties.' + key
			scoped_properties[key] = { 'value': value }
		properties = { 'properties': scoped_properties }
		url = '/api/v0/staged/products/' + product_settings['guid']
		put_json(url + '/networks_and_azs', networks_and_azs)
		put_json(url + '/properties', properties)
		for job_guid, job_resource_config in resource_config.items():
			resource_config_url = url + '/jobs/' + job_guid + '/resource_config'
			merged_job_resource_config = get(resource_config_url).json()
			merged_job_resource_config.update(job_resource_config)
			put_json(url + '/jobs/' + job_guid + '/resource_config', merged_job_resource_config)
	elif version[:2] == [1, 7] or version[:2] == [1, 6]:
		if job_properties:
			print('Warning: setting job-specific properties and resource config is only supported for PCF 1.8+', file=sys.stderr)
			print('         job-specific properties and resource config will not be set', file=sys.stderr)
		post_yaml('/api/installation_settings', 'installation[file]', settings)
	else:
		print("PCF version ({}) is unsupported, but we'll give it a try".format('.'.join(str(x) for x in version)))
		try:
			post_yaml('/api/installation_settings', 'installation[file]', settings)
		except:
			print(file='Configuration failed, probably due to incompatible PCF version.')
			sys.exit(1)

def get_changes(product = None, deploy_errands = None, delete_errands = None):
	version = get_version()
	if version[0] == 1 and version[1] >= 8:
		return build_changes_1_8(deploy_errands, delete_errands)
	elif version[0] == 1 and version[1] == 7:
		return build_changes_1_7(product, deploy_errands, delete_errands)
	else:
		return None

def build_changes_1_8(deploy_errands, delete_errands):
	changes = get('/api/v0/staged/pending_changes').json()
	for product_change in changes['product_changes']:
		if product_change['action'] in ['install', 'update']:
			product_change['errands'] = [
				e for e in product_change['errands']
				if deploy_errands is None or e['name'] in deploy_errands
			]
	for product_change in changes['product_changes']:
		if product_change['action'] == 'delete':
			product_change['errands'] = [
				e for e in product_change['errands']
				if delete_errands is None or e['name'] in delete_errands
			]
	return changes

def build_changes_1_7(product, deploy_errands, delete_errands):
	if deploy_errands is None and delete_errands is None:
		print('You must specify --deploy-errands or --delete-errands on PCF 1.7,', file=sys.stderr)
		print('since we cannot reliably discover them on that version', file=sys.stderr)
		sys.exit(1)
	deployed = [p for p in get('/api/v0/deployed/products').json()]
	staged   = [p for p in get('/api/v0/staged/products').json()]
	install  = [p for p in staged if p["guid"] not in [g["guid"] for g in deployed]]
	delete   = [p for p in deployed if p["guid"] not in [g["guid"] for g in staged]]
	update   = [p for p in deployed if p["guid"] in [g["guid"] for g in staged if not g["guid"].startswith('cf-')]]
	# update = []
	if product is not None:
		install = [p for p in install if p["guid"].startswith(product + '-')]
		delete  = [p for p in delete if p["guid"].startswith(product + '-')]
		update  = [p for p in update if p["guid"].startswith(product + '-')]
	for p in install + update:
		p['errands'] = []
		if deploy_errands is None:
			deploy_errands = []
		for deploy_errand in deploy_errands:
			p['errands'].append({'name': deploy_errand, 'post_deploy': True})
	for p in delete:
		p['errands'] = []
		if delete_errands is None:
			delete_errands = []
		for delete_errand in delete_errands:
			p['errands'].append({'name': delete_errand, 'pre_delete': True})
	changes = {'product_changes': [{
			'guid': p['guid'],
			'errands': p.get('errands', []),
			'action': 'install' if p in install else 'delete' if p in delete else 'update'
		}
		for p in install + delete + update
	]}
	return changes

def get_cfinfo():
	settings = get('/api/installation_settings').json()
	settings = [ p for p in settings['products'] if p['identifier'] == 'cf' ]
	if len(settings) < 1:
		print('Elastic Runtime is not installed', file=sys.stderr)
		sys.exit(1)
	settings = settings[0]
	jobs = settings['jobs']
	cc_properties = [ j for j in jobs if j['identifier'] == 'cloud_controller' ][0]['properties']
	system_domain = [ p for p in cc_properties if p['identifier'] == 'system_domain' ][0]['value']
	apps_domain = [ p for p in cc_properties if p['identifier'] == 'apps_domain' ][0]['value']
	uaa_properties = [ j for j in jobs if j['identifier'] == 'uaa' ][0]['properties']
	admin_credentials = [ c for c in uaa_properties if c['identifier'] == 'admin_credentials' ][0]['value']
	system_services_credentials = [ c for c in uaa_properties if c['identifier'] == 'system_services_credentials' ][0]['value']
	return {
		'system_domain': system_domain,
		'apps_domain': apps_domain,
		'admin_username': admin_credentials['identity'],
		'admin_password': admin_credentials['password'],
		'system_services_username': system_services_credentials['identity'],
		'system_services_password': system_services_credentials['password'],
	}

def logs(install_id):
	if install_id is None:
		install_id = last_install()
		if install_id == 0:
			print('No installation has ever been performed', file=sys.stderr)
			sys.exit(1)
	lines_shown = 0
	running = True
	while running:
		install_status = get('/api/installation/' + str(install_id)).json()['status']
		running = install_status == 'running'
		log_lines = get('/api/installation/' + str(install_id) + '/logs').json()['logs'].splitlines()
		for line in log_lines[lines_shown:]:
			if not line.startswith('{'):
				print(' ', line.encode('utf-8'))
		lines_shown = len(log_lines)
		if running:
			time.sleep(1)
	if not install_status.startswith('succ'):
		print('- install finished with status:', install_status, file=sys.stderr)
		sys.exit(1)

def install_exists(id):
	response = get('/api/installation/' + str(id), check=False)
	return response.status_code == requests.codes.ok

def last_install(lower=0, upper=1, check=install_exists):
	if lower == upper:
		return lower
	if check(upper):
		return last_install(upper, upper * 2, check=check)
	middle = (lower + upper + 1) // 2
	if check(middle):
		return last_install(middle, upper, check=check)
	else:
		return last_install(lower, middle - 1, check=check)

def unlock():
	creds = get_credentials()
	passphrase = creds.get('opsmgr').get('password')
	body = { 'passphrase': passphrase }
	waiting = False
	while True:
		try:
			response = put('/api/v0/unlock', body, check=False)
			if response.status_code == requests.codes.ok:
				if waiting:
					print(' ok')
				return
			if response.status_code == 404:
				if waiting:
					print(' ok')
				print("Unlock not required for this version")
				return
			if response.status_code != 503 and response.status_code != 502:
				print('-', response.status_code, response.request.url, file=sys.stderr)
				try:
					errors = response.json()["errors"]
					print('- '+('\n- '.join(json.dumps(errors, indent=4).splitlines())), file=sys.stderr)
				except:
					print(response.text, file=sys.stderr)
				sys.exit(1)
		except requests.exceptions.ConnectionError:
			pass
		if waiting:
			sys.stdout.write('.')
			sys.stdout.flush()
		else:
			sys.stdout.write('Waiting for ops manager ')
			sys.stdout.flush()
			waiting = True
		time.sleep(5)
		continue
