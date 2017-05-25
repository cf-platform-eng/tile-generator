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
import yaml
import json
import time
import click
import subprocess

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(PATH, os.path.join('..', 'lib')))
from . import opsmgr
from . import erb

@click.group()
@click.option('-t', '--target')
@click.option('-n', '--non-interactive', is_flag=True)
def cli(target, non_interactive):
	opsmgr.get_credentials(target, non_interactive)

@cli.command('ssh')
@click.argument('argv', nargs=-1)
@click.option('--debug', '-d', is_flag=True)
def ssh_cmd(argv, debug=False):
	opsmgr.ssh(argv, debug=debug)

@cli.command('reboot')
@click.option('--yes-i-am-sure', '-y', is_flag=True)
def reboot_cmd(yes_i_am_sure=False):
	if not yes_i_am_sure:
		print('Rebooting in', end="")
		for i in range(10, 0, -1):
			sys.stdout.write(' ' +str(i))
			sys.stdout.flush()
			time.sleep(1)
		print()
	opsmgr.ssh(['sudo reboot now'], silent=True)
	time.sleep(10) # Allow system time to go down before we ping the API
	opsmgr.unlock()

@cli.command('unlock')
def unlock_cmd():
	opsmgr.unlock()

@cli.command('products')
def products_cmd():
	products = opsmgr.get_products()
	for product in products:
		print("-", product["name"], product["product_version"], "(installed)" if product["installed"] else "")

@cli.command('changes')
def changes_cmd():
	changes = opsmgr.get_changes()
	if changes is None:
		print('This command is only available for PCF 1.7 and beyond.', file=sys.stderr)
		sys.exit(1)
	for p in changes['product_changes']:
		print(p['action'], p['guid'])
		for e in p['errands']:
			print('-', e['name'])

@cli.command('is-available')
@click.argument('product')
@click.argument('version', None, required=False)
def is_available_cmd(product, version):
	products = opsmgr.get_products()
	matches = [ p for p in products if p['name'] == product and (version is None or p['product_version'] == version) ]
	if len(matches) < 1:
		print('No match found for product', product, 'version', version, file=sys.stderr)
		sys.exit(1)

@cli.command('is-installed')
@click.argument('product')
@click.argument('version', None, required=False)
def is_installed_cmd(product, version):
	products = opsmgr.get_products()
	matches = [ p for p in products if p['name'] == product and (version is None or p['product_version'] == version) and p['installed'] ]
	if len(matches) < 1:
		print('Product', product, 'version', version, 'is not installed', file=sys.stderr)
		sys.exit(1)

@cli.command('configure')
@click.argument('product')
@click.argument('properties_file', None, required=False)
@click.option('--strict', is_flag=True)
@click.option('--skip-validation', is_flag=True)
@click.option('-n', '--network')
def configure_cmd(product, properties_file, strict=False, skip_validation=False, network=None):
	properties = {}
	if properties_file is not None:
		with open(properties_file) as f:
			properties = yaml.safe_load(f)
	opsmgr.configure(product, properties, strict, skip_validation, network)

@cli.command('settings')
@click.argument('product', None, required=False)
def settings_cmd(product):
	settings = opsmgr.get('/api/installation_settings').json()
	if product is not None:
		settings = [ p for p in settings['products'] if p['identifier'] == product ]
		if len(settings) < 1:
			print('No settings found for product', product, file=sys.stderr)
			sys.exit(1)
		settings = settings[0]
	print(json.dumps(settings, indent=4))

@cli.command('cf-info')
def cf_info_cmd():
	cfinfo = opsmgr.get_cfinfo()
	for key in sorted(cfinfo):
		print('-', key + ':', cfinfo[key])

@cli.command('import')
@click.argument('tile')
def import_cmd(tile):
	opsmgr.upload('/api/products', tile)
	print('-', 'Tile', tile, 'imported successfully. You can run `pcf install` to load it.')

@cli.command('install')
@click.argument('product')
@click.argument('version')
def install_cmd(product, version):
	products = opsmgr.get_products()
	matches = [ p for p in products if p['name'] == product and p['installed'] ]
	if len(matches) < 1:
		payload = {
			'name': product,
			'product_version': version,
		}
		opsmgr.post('/api/installation_settings/products', payload)
	else:
		payload = {
			'to_version': version
		}
		response = opsmgr.put('/api/installation_settings/products/' + matches[0]['guid'], payload, check=False)
		if response.status_code == 422:
			errors = response.json()["errors"]
			for error in errors:
				if error.endswith(' is already in use.'):
					print('-','version already installed')
					return
		opsmgr.check_response(response)

@cli.command('uninstall')
@click.argument('product')
@click.argument('version', None, required=False)
def uninstall_cmd(product, version):
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	for match in matches:
		if version and 'product_version' in match:
			if match['product_version'] == version:
				opsmgr.delete('/api/installation_settings/products/' + match['guid'])
		else:
			opsmgr.delete('/api/installation_settings/products/' + match['guid'])

@cli.command('delete-unused-products')
def delete_unused_products_cmd():
	opsmgr.delete('/api/products')

@cli.command('backup')
@click.argument('backup_file')
def backup_cmd(backup_file):
	response = opsmgr.get('/api/installation_asset_collection', stream=True)
	with open(backup_file, 'wb') as f:
		for chunk in response.iter_content(1024):
			f.write(chunk)

@cli.command('restore')
@click.argument('backup_file')
def restore_cmd(backup_file):
	creds = get_credentials()
	with open(backup_file, 'rb') as f:
		payload = { 'installation[file]': f, 'password': creds['opsmgr']['password'] }
		opsmgr.post('/api/installation_asset_collection', f)

@cli.command('cleanup')
@click.argument('product')
def cleanup_cmd(product):
	#
	# Attempt 1 - Delete any uninstalled versions
	#
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	for match in matches:
		print('- attempting to delete', match['name'], file=sys.stderr)
		opsmgr.delete('/api/installation_settings/products/' + match['guid'])
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	if len(matches) < 1:
		sys.exit(0)
	if len(matches) > 1:
		print('- more than one match remains installed', file=sys.stderr)
		sys.exit(1)
	#
	# Attempt 2 - Uninstall deployed version
	#
	match = matches[0]
	print('- product was deployed, applying changes to uninstall it', file=sys.stderr)
	apply_changes_cmd()
	opsmgr.delete('/api/products')
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	if len(matches) < 1:
		sys.exit(0)
	#
	# Attempt 3 - Re-deploy with errands disabled, then uninstall
	#
	match = matches[0]
	print('- uninstall appears to have failed', file=sys.stderr)
	print('- re-deploying with disabled errands', file=sys.stderr)
	opsmgr.disable_errands(product)
	apply_changes_cmd()
	print('- uninstalling with disabled errands', file=sys.stderr)
	opsmgr.delete('/api/installation_settings/products/' + match['guid'])
	apply_changes_cmd()
	opsmgr.delete('/api/products')
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	if len(matches) > 0:
		print('- failed to uninstall', file=sys.stderr)
		sys.exit(1)

@cli.command('apply-changes')
@click.option('--product', help='product to select errands from. Only valid in combination with -deploy-errands or --delete-errands.')
@click.option('--deploy-errands', help='Comma separated list of errands to run after install/update. For example: "deploy-all,configure-broker"')
@click.option('--delete-errands', help='Comma separated list of errands to run before delete. For example: "pre_delete"')
def apply_changes_cmd(product, deploy_errands, delete_errands):
	body = None
	version = opsmgr.get_version()
	pre_1_10 = version[0] == 1 and version[1] < 10
	if pre_1_10:
		enabled_errands = []
		deploy_errand_list = None if deploy_errands is None else deploy_errands.split(',')
		delete_errand_list = None if delete_errands is None else delete_errands.split(',')
		changes = opsmgr.get_changes(product, deploy_errand_list, delete_errand_list)
		if changes is not None:
			if len(changes['product_changes']) == 0:
				print('Nothing to do', file=sys.stderr)
				return
			for p in changes['product_changes']:
				post_deploy = serialize_errands(p, 'post_deploy', 'post_deploy_errands')
				enabled_errands.extend(post_deploy)
				pre_delete = serialize_errands(p, 'pre_delete', 'pre_delete_errands')
				enabled_errands.extend(pre_delete)
		body = '&'.join(enabled_errands)
	in_progress = None
	install_id = None
	while install_id is None:
		if pre_1_10:
			response = opsmgr.post('/api/installation?ignore_warnings=true', body, check=False)
		else:
			response = opsmgr.post('/api/v0/installations?ignore_warnings=true', body, check=False)
		if response.status_code == 422 and "Install in progress" in response.json()["errors"]:
			if in_progress is None:
				print('Waiting for in-progress installation to complete', file=sys.stderr)
				in_progress = opsmgr.last_install()
			time.sleep(10)
			if opsmgr.install_exists(in_progress + 1):
				install_id = in_progress + 1
				break
			continue
		elif response.status_code == 422:
			print('-', response.status_code, response.request.url, file=sys.stderr)
			try:
				errors = response.json()["errors"]
				print('- '+('\n- '.join(json.dumps(errors, indent=4).splitlines())), file=sys.stderr)
			except:
				print(response.text, file=sys.stderr)
			sys.exit(2)
		opsmgr.check_response(response)
		install = response.json()['install']
		install_id = install['id']
		break
	opsmgr.logs(install_id)

def serialize_errands(product, type, form_key):
	matching_errands = [e for e in (product['errands']) if e.get(type, False)]
	serialized = []
	for matching_errand in matching_errands:
		serialized.append('enabled_errands[%s][%s][]=%s' % (product['guid'], form_key, matching_errand['name']))

	return serialized

@cli.command('logs')
@click.argument('install_id', None, required=False)
def logs_cmd(install_id=None):
	opsmgr.logs(install_id)

@cli.command('test-errand')
@click.argument('tile_repo')
@click.argument('errand_name')
def test_errand_cmd(tile_repo, errand_name):
	print('test-errand is currently disabled while we work on improving it (issue #134)', file=sys.stderr)
	sys.exit(1)
	rendered_errand = erb.render(errand_name, tile_repo)
	env = os.environ
	env['PACKAGE_PATH'] = os.path.join(tile_repo, 'release/blobs')
	os.execlpe('bash', 'bash', rendered_errand, env)

@cli.command('target')
@click.option('--org','-o',default=None)
@click.option('--space','-s',default=None)
def target_cmd(org, space):
	cf = opsmgr.get_cfinfo()
	login = [
		'cf', 'login',
		'-a', 'api.' + cf['system_domain'],
		'--skip-ssl-validation',
		'-u', cf['admin_username'],
		'-p', cf['admin_password'],
	]
	if org is not None:
		login += [ '-o', org ]
	if space is not None:
		login += [ '-s', space ]
	subprocess.call(login)

@cli.command('curl')
@click.argument('path')
@click.option('--request', '-X', type=click.Choice('GET POST PUT DELETE'.split()), default='GET')
@click.option('--data', '-d', default=None)
def curl_cmd(path, request, data):
	if data and os.path.isfile(data):
		with open(data, 'r') as infile:
			data = infile.read()
	if request == 'GET':
		response = opsmgr.get(path)
	elif request == 'POST':
		response = opsmgr.post(path, data)
	elif request == 'PUT':
		response = opsmgr.put(path, data)
	elif request == 'DELETE':
		response = opsmgr.delete(path)
	else:
		print('Unsupported request type: ' + request, file=sys.stderr)
		sys.exit(1)
	print(json.dumps(response.json(), indent=2))

@cli.command('errands')
@click.argument('product')
def errands_cmd(product):
	products = opsmgr.get('/api/v0/staged/products').json()
	guid = [p for p in products if p['type'] == product][0]['guid']
	errands = opsmgr.get('/api/v0/staged/products/' + guid + '/errands').json()['errands']
	print(json.dumps(errands, indent=4))

@cli.command('disable-errand')
@click.argument('product')
@click.argument('errand')
def disable_errand_cmd(product, errand):
	products = opsmgr.get('/api/v0/staged/products').json()
	guid = [p for p in products if p['type'] == product][0]['guid']
	errands = opsmgr.get('/api/v0/staged/products/' + guid + '/errands').json()['errands']
	errands = [e for e in errands if e['name'] == errand]
	for e in errands:
		if e.get('post_deploy', None) is not None:
			e['post_deploy'] = False
		if e.get('pre_delete', None) is not None:
			e['pre_delete'] = False
	if len(errands) > 0:
		opsmgr.put_json('/api/v0/staged/products/' + guid + '/errands', { 'errands': errands })

@cli.command('enable-errand')
@click.argument('product')
@click.argument('errand')
def enable_errand_cmd(product, errand):
	products = opsmgr.get('/api/v0/staged/products').json()
	guid = [p for p in products if p['type'] == product][0]['guid']
	errands = opsmgr.get('/api/v0/staged/products/' + guid + '/errands').json()['errands']
	errands = [e for e in errands if e['name'] == errand]
	for e in errands:
		if e.get('post_deploy', None) is not None:
			e['post_deploy'] = True
		if e.get('pre_delete', None) is not None:
			e['pre_delete'] = True
	if len(errands) > 0:
		opsmgr.put_json('/api/v0/staged/products/' + guid + '/errands', { 'errands': errands })

@cli.command('version')
def version_cmd():
	version = opsmgr.get_version()
	print('.'.join([ str(x) for x in version ]))

@cli.command('credentials')
def credentials_cmd():
	creds = opsmgr.get_credentials()
	creds['opsmgr'].pop('ssh_key', None)
	cf = opsmgr.get_cfinfo()
	creds['cf'] = {
		'url': 'https://api.' + cf['system_domain'],
		'username': cf['admin_username'],
		'password': cf['admin_password'],
		'app_domain': cf['apps_domain'],
		'sys_domain': cf['system_domain'],
	}
	print(yaml.safe_dump(creds, default_flow_style=False, explicit_start=True), end='')

@cli.command('history')
def history_cmd():
	history = opsmgr.get_history()
	print(json.dumps(history, indent=4))

@cli.command('upload-stemcell')
@click.argument('stemcell-file')
def upload_stemcell_cmd(stemcell_file):
	opsmgr.post('/api/v0/stemcells', None, files={'stemcell[file]': open(stemcell_file, 'rb')})
	print('stemcell uploaded')

@cli.command('stemcells')
def stemcells_cmd():
	stemcells = opsmgr.get_stemcells()
	print(json.dumps(stemcells, indent=4))

def main():
	try:
		cli()
	except Exception as e:
		print(e, file=sys.stderr)
		sys.exit(1)

if __name__ == '__main__':
	main()
