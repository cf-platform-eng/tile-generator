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



import fcntl
import glob
import json
import os
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import yaml

from pexpect import pxssh
from requests_toolbelt import MultipartEncoderMonitor
try:
	# Python 3
	from urllib.parse import urlparse
except ImportError:
	# Python 2
	from urllib.parse import urlparse

import requests
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
	raise Exception('Did not find a target repository named ' + dirname)

def get_credential_dir(update=False):
	dir = find_credential_dir()
	if update:
		devnull = open(os.devnull,"w")
		subprocess.call(['git', 'pull'], cwd=dir, stdout=devnull, stderr=devnull)
	return dir

def is_poolsmiths_env(creds):
	return 'ops_manager' in creds

def get_credentials(target=None, non_interactive=False):
	if get_credentials.credentials is not None:
		return get_credentials.credentials
	ssh_key = None
	if target is not None:
		credential_dir = get_credential_dir(update=(not non_interactive))
		credential_file = os.path.join(credential_dir, target + '.yml')
		private_key_file = os.path.join(credential_dir, target + '.opsman_rsa')
		if os.path.isfile(private_key_file):
			with open(private_key_file, 'rb') as keyfile:
				ssh_key = keyfile.read()
	else:
		# This default handles the case where we are executing from within a
		# concourse pool-resource repository, where the claimed PCF instance
		# metadata is available in a file named './metadata'
		credential_file = 'metadata'
	try:
		with open(credential_file) as cred_file:
			creds = yaml.safe_load(cred_file)
			if is_poolsmiths_env(creds):
				creds['opsmgr'] = creds['ops_manager']
				creds['opsmgr']['ssh_key'] = creds['ops_manager_private_key']
			creds['opsmgr']
			creds['opsmgr']['url']
			creds['opsmgr']['username']
			creds['opsmgr']['password']
			creds['opsmgr']['ssh_key'] = creds['opsmgr'].get('ssh_key', ssh_key)
			get_credentials.credentials = creds
	except KeyError as e:
		raise Exception('Credential file is missing a value:' + e.message)
	except IOError as e:
		if target is not None:
			raise Exception('No target named {} found in {}'.format(target, credential_dir))
		else:
			raise Exception(
				'You must either specify a target using the --target option,\n'
				'or execute this command from within a directory that has credentials\n'
				'in a file named "metadata" (like a claimed Concourse pool resource)\n'
			)
	return creds

get_credentials.credentials = None

def set_credentials(credentials):
	get_credentials.credentials = credentials

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

def post(url, payload, files=None, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	response = requests.post(url, auth=auth(creds), verify=False, data=payload, files=files)
	check_response(response, check)
	return response

def post_yaml(url, filename, payload):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	files = { filename: yaml.safe_dump(payload) }
	response = requests.post(url, auth=auth(creds), verify=False, files=files)
	check_response(response)
	return response

class ProgressBar:
	def __init__(self):
		self.last_update = 0
		self.update_every = 2 * 1024 * 1024
		sys.stdout.write('0%')
		sys.stdout.flush()

	def update(self, monitor):
		self.update_every = min(self.update_every, monitor.len / 30)
		if monitor.bytes_read - self.last_update >= self.update_every:
			sys.stdout.write('.')
			old_percent = float(self.last_update) / monitor.len
			new_percent = float(monitor.bytes_read) / monitor.len
			for step in range(90, 0, -10):
				step /= 100.0
				if new_percent >= step > old_percent:
					sys.stdout.write('{:.0%}'.format(step))
					break
			sys.stdout.flush()
			self.last_update = monitor.bytes_read

def upload(url, filename, check=True):
	creds = get_credentials()
	url = creds.get('opsmgr').get('url') + url
	multipart = MultipartEncoderMonitor.from_fields(
		fields={
			'product[file]': ('product[file]', open(filename, 'rb'), 'application/octet-stream')
		},
		callback=ProgressBar().update
	)
	response = requests.post(url,
		auth=auth(creds),
		verify=False,
		data=multipart,
		headers={ 'Content-Type': multipart.content_type }
	)
	sys.stdout.write('.100%\n')
	sys.stdout.flush()
	if response.status_code == 422:
		errors = response.json()["errors"]
		try:
			product = errors.get('product', [])
			for reason in product:
				if reason.startswith('Metadata already exists for'):
					print('-','version already uploaded')
					return response
		except:
			pass
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
		message = '- {} {}\n'.format(response.status_code, response.request.url)
		try:
			errors = response.json()["errors"]
			for line in json.dumps(errors, indent=4).splitlines():
				message += '- ' + line + '\n'
		except:
			message += response.text
		raise Exception(message)

def ssh(command=None, login_to_bosh=True, quiet=False):
	def print_if(message):
		if not quiet: print(message)

	# Note that the prompt matching uses regex
	bosh2_username_prompt = 'Email \(\): '
	bosh2_password_prompt = 'Password \(\): '
	sudo_prompt = '\[sudo\] password for .*:'
	sudo_fail_prompt = 'Sorry, try again.'

	prompt_wait_timeout = 3

	creds = get_credentials()
	url = creds.get('opsmgr').get('url')
	host = urlparse(url).hostname
	ssh_key = creds.get('opsmgr').get('ssh_key', None)

	print_if('Attempting to connect to %s...' % host)
	global session # Needs to be a global to be used in sigwinch_passthrough.
	session = pxssh.pxssh(options={
									"StrictHostKeyChecking": "no",
									"UserKnownHostsFile": "/dev/null"})
	if ssh_key is not None:
		print_if('Logging in with a key file...')
		with tempfile.NamedTemporaryFile('wb') as keyfile:
			keyfile.write(ssh_key)
			keyfile.flush()

			session.login(host, username='ubuntu', ssh_key=keyfile.name, quiet=True)
	else:
		print_if('Logging in with using a username and password...')
		session.login(host, username='ubuntu', 
					  password=creds.get('opsmgr').get('password'), quiet=True)

	if login_to_bosh:
		# Setup the env
		print_if('Exporting needed bosh environment variables...')
		director_creds = get('/api/v0/deployed/director/credentials/director_credentials').json()
		director_manifest = get('/api/v0/deployed/director/manifest').json()
		if 'jobs' in director_manifest: # PCF 2.2 and earlier
			director_address = director_manifest['jobs'][0]['properties']['director']['address']
		else: # PCF 2.3 and later
			director_address = director_manifest['instance_groups'][0]['properties']['director']['address']
		session.sendline('export BOSH_ENVIRONMENT="{}"'.format(director_address))
		session.sendline('export BOSH_CA_CERT="/var/tempest/workspaces/default/root_ca_certificate"')
		
		bosh2_username = director_creds['credential']['value']['identity']
		print_if('Logging into bosh2 as %s...' % bosh2_username)
		session.sendline('which bosh2 || alias bosh2=bosh') # In Ops Manager 2.0+, there is just bosh (which is v2).
		session.sendline('bosh2 login')
		session.expect(bosh2_username_prompt, timeout=prompt_wait_timeout)
		session.send(bosh2_username)
		session.sendcontrol('m') # For some reason bosh2 login requires to send enter manually
		session.expect(bosh2_password_prompt, timeout=prompt_wait_timeout)
		session.send(director_creds['credential']['value']['password'])
		session.sendcontrol('m') # For some reason bosh2 login requires to send enter manually
	
	if command:
		session.sync_original_prompt()
		print_if('Sending command: "%s"...' % command)
		session.sendline(command)

		# Try to be smart about sudo
		if 'sudo' in command:
			resp = session.expect([sudo_prompt, session.PROMPT], timeout=prompt_wait_timeout)
			if resp == 0: # We got the sudo password prompt
				print_if('A sudo password prompt was detected. Attempting to login...')
				session.sendline(creds.get('opsmgr').get('password'))
				resp = session.expect([sudo_fail_prompt, session.PROMPT], timeout=prompt_wait_timeout)
				if resp == 0: # Password was wrong
					raise Exception('UNAUTHORIZED: Password was incorrect.')
			print(session.before.strip(command).strip())
		else:
			session.prompt(timeout=prompt_wait_timeout)
			print(session.before.strip(command).strip())
	else:
		# Get us a native prompt
		print_if('Sourcing .bashrc for a correct shell..')
		session.sendline('source .bashrc')

		# This is the recommended way to keep parent window resizes in sync with the child
		# http://pexpect.sourceforge.net/pxssh.html
		def sigwinch_passthrough (sig, data):
			s = struct.pack("HHHH", 0, 0, 0, 0)
			a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ , s))
			session.setwinsize(a[0],a[1])
		signal.signal(signal.SIGWINCH, sigwinch_passthrough)
		os.kill(os.getpid(), signal.SIGWINCH) # Set initial window size.

		# Hand the shell off and make it interactive
		session.interact()

def get_products():
	available_products = get('/api/products').json()
	installed_products = get('/api/installation_settings').json()['products']
	products = [{
		'guid': p['guid'],
		'name': p['identifier'],
		'product_version': p['product_version'],
		'installed': True,
	} for p in installed_products ]
	for p in available_products:
		installed = [ i for i in products if p['name'] == i['name'] and p['product_version'] == i['product_version'] ]
		if len(installed) == 0:
			p['installed'] = False
			products += [ p ]
	return products

def get_version():
	# 1.7 and 1.8 have version in the diagnostic report.
	response = get('/api/v0/diagnostic_report', check=False)
	if response.status_code == requests.codes.ok:
		diag = response.json()
		version = diag['versions']['release_version']
		version = version.split('-')[0]
		return [ int(x) for x in version.split('.') ]

	raise Exception('Error: could not determine Ops Manager version.')

def get_job_guid(job_identifier, jobs_settings):
	for job in jobs_settings:
		if job.get('identifier', None) == job_identifier:
			return job['guid']
	print('Warning: Could not find job with identifier', job_identifier, file=sys.stderr)
	return None

def configure(product, properties, strict=False, skip_validation=False, network=None):
	settings = get('/api/installation_settings').json()
	infrastructure = settings['infrastructure']
	product_settings = [ p for p in settings['products'] if p['identifier'] == product ]
	if len(product_settings) < 1:
		raise Exception('Product {} does not appear to be installed'.format(product))
	product_settings = product_settings[0]
	properties = properties if properties is not None else {}
	#
	# Make sure Elastic Runtime tile is installed
	#
	cf = [ p for p in settings['products'] if p['identifier'] == 'cf' ]
	if len(cf) < 1:
		raise Exception('Required product Elastic Runtime is missing')
	#
	# Use the Elastic Runtime stemcell (unless the --strict option was used)
	#
	if not strict:
		if 'stemcell' in cf[0]:
			stemcell = cf[0]['stemcell']
		elif 'stemcells' in cf[0]:
			stemcell = cf[0]['stemcells'][0]
		else:
			raise Exception("Cannot find cf stemcell to use")
		print('- Using stemcell', stemcell['name'], 'version', stemcell['version'])
		product_settings['stemcell'] = stemcell
		post_yaml('/api/installation_settings', 'installation[file]', settings)
	#
	# Use the first availability zone (skip this for Azure, which doesn't use them)
	#
	availability_zones = infrastructure.get('availability_zones', [])
	if 'availability_zones' in infrastructure:
		product_settings['availability_zone_references'] = [ az['guid'] for az in availability_zones ]
		product_settings['singleton_availability_zone_reference'] = availability_zones[0]['guid']
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
		message = 'Input file is missing required properties:\n'
		message += '- ' + '\n- '.join(missing_properties)
		raise Exception(message)
	#
	# Normalize az properties
	#
	for az in availability_zones:
		if az.get('name', None) is None:
			az['name'] = az['iaas_identifier']
	#
	# Default networks if not provided (preserves prior behavior)
	#
	if network is None:
		network = infrastructure['networks'][0]['name']
	service_network = ([ n for n in infrastructure['networks'] if n.get('service_network', False) ] + [ None ])[0]
	if service_network is not None:
		service_network = service_network['name']
	#
	# Update using the appropriate API for the Ops Manager version
	#
	version = get_version()
	if version[0] > 1 or (version[0] == 1 and version[1] >= 8):
		url = '/api/v0/staged/products/' + product_settings['guid']
		if 'availability_zones' in infrastructure:
			networks_and_azs = {
				'networks_and_azs': {
					'singleton_availability_zone': { 'name': availability_zones[0]['name'] },
					'other_availability_zones': [ { 'name': az['name'] } for az in availability_zones ],
					'network': { 'name': network },
				}
			}
			if service_network is not None:
				networks_and_azs['networks_and_azs']['service_network'] = { 'name': service_network }
			put_json(url + '/networks_and_azs', networks_and_azs)
		scoped_properties = {}
		resource_config = {}
		for job, job_properties in jobs_properties.items():
			if 'resource_config' in job_properties:
				job_resource_config = job_properties.pop('resource_config')
				job_guid = get_job_guid(job, product_settings.get('jobs', []))
				if job_guid is None:
					continue
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
		put_json(url + '/properties', properties)
		for job_guid, job_resource_config in resource_config.items():
			resource_config_url = url + '/jobs/' + job_guid + '/resource_config'
			merged_job_resource_config = get(resource_config_url).json()
			merged_job_resource_config.update(job_resource_config)
			put_json(url + '/jobs/' + job_guid + '/resource_config', merged_job_resource_config)

	else:
		print("PCF version ({}) is unsupported, but we'll give it a try".format('.'.join(str(x) for x in version)))
		try:
			post_yaml('/api/installation_settings', 'installation[file]', settings)
		except:
			raise Exception('Configuration failed, probably due to incompatible PCF version.')

def get_changes(product = None, deploy_errands = None, delete_errands = None):
	return build_changes(deploy_errands, delete_errands)

def build_changes(deploy_errands, delete_errands):
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
		raise Exception(
			'You must specify --deploy-errands or --delete-errands on PCF 1.7,\n'
			'since we cannot reliably discover them on that version'
		)
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
	cf_settings = [ p for p in settings['products'] if p['identifier'] == 'cf' ]
	if len(cf_settings) < 1:
		raise Exception('Elastic Runtime is not installed')
	cf_settings = cf_settings[0]
	jobs = cf_settings['jobs']
	cc_properties = [ j for j in jobs if j['identifier'] == 'cloud_controller' ][0]['properties']
	system_domain = [ p for p in cc_properties if p['identifier'] == 'system_domain' ][0]['value']
	apps_domain = [ p for p in cc_properties if p['identifier'] == 'apps_domain' ][0]['value']
	uaa_properties = [ j for j in jobs if j['identifier'] == 'uaa' ][0]['properties']
	admin_credentials = [ c for c in uaa_properties if c['identifier'] == 'admin_credentials' ][0]['value']
	system_services_credentials = [ c for c in uaa_properties if c['identifier'] == 'system_services_credentials' ][0]['value']
	return {
		'system_domain': system_domain,
		'apps_domain': apps_domain,
		'schema_version': settings.get("installation_schema_version"),
		'admin_username': admin_credentials['identity'],
		'admin_password': admin_credentials.get('password', None),
		'system_services_username': system_services_credentials['identity'],
		'system_services_password': system_services_credentials.get('password', None)
	}

def logs(install_id):
	if install_id is None:
		install_id = last_install()
		if install_id == 0:
			raise Exception('No installation has ever been performed')
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
		raise Exception('- install finished with status: {}'.format(install_status))

def install_exists(id):
	response = get('/api/installation/' + str(id), check=False)
	return response.status_code == requests.codes.ok

def last_install(lower=0, upper=1, check=install_exists):
	try:
		installations = get('/api/v0/installations', check=False).json()['installations']
		installations = [ i['id'] for i in installations]
		return sorted([ 0 ] + installations)[-1]
	except:
		pass
	if lower == upper:
		return lower
	if check(upper):
		return last_install(upper, upper * 2, check=check)
	middle = (lower + upper + 1) // 2
	if check(middle):
		return last_install(middle, upper, check=check)
	else:
		return last_install(lower, middle - 1, check=check)

def get_history():
	try:
		installations = get('/api/v0/installations', check=False).json()['installations']
		return installations
	except:
		pass
	installations = []
	install_id = 1
	while True:
		response = get('/api/installation/' + str(install_id), check=False)
		if response.status_code != requests.codes.ok:
			break
		installations += [ response.json() ]
		install_id += 1
	return installations

def get_status():
	id  = last_install()
	if id == 0:
		return { 'status': 'idle' }
	return get('/api/installation/' + str(id)).json()

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
				message = '- {} {}\n'.format(response.status_code, response.request.url)
				try:
					errors = response.json()["errors"]
					message += '- '+('\n- '.join(json.dumps(errors, indent=4).splitlines()))
				except:
					message += response.text
				raise Exception(message)
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

def get_stemcells():
	response = get('/api/v0/diagnostic_report', check=False)
	if response.status_code == requests.codes.ok:
		diag = response.json()
		stemcells = diag.get('stemcells') or diag.get('available_stemcells') or []
		return stemcells
	return []
