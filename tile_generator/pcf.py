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
def cli():
	pass

@cli.command('ssh')
def ssh_cmd():
	opsmgr.ssh()

@cli.command('products')
def products_cmd():
	products = opsmgr.get_products()
	for product in products:
		print("-", product["name"], product["product_version"], "(installed)" if product["installed"] else "")

@cli.command('changes')
def deployed_cmd():
	try:
		changes = opsmgr.get_changes()
		for p in changes['product_changes']:
			print(p['action'], p['guid'])
			for e in p['errands']:
				print('-', e['name'])
	except:
		print('This command is only available for PCF 1.7 and beyond.', file=sys.stderr)
		sys.exit(1)

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
@click.argument('properties_file')
@click.option('--strict', is_flag=True)
def configure_cmd(product, properties_file, strict=False):
	with open(properties_file) as f:
		properties = yaml.safe_load(f)
	opsmgr.configure(product, properties, strict)

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
@click.argument('zipfile')
def import_cmd(zipfile):
	opsmgr.upload('/api/products', zipfile)

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
		opsmgr.put('/api/installation_settings/products/' + matches[0]['guid'], payload)

@cli.command('uninstall')
@click.argument('product')
def install_cmd(product):
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [ p for p in products if p['type'] == product ]
	for match in matches:
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
@click.option('--deploy-errands', help='Comma separated list of errands to run after install/update. For example: "deploy-all,configure-broker"')
@click.option('--delete-errands', help='Comma separated list of errands to run before delete. For example: "pre_delete"')
def apply_changes_cmd(deploy_errands, delete_errands):
	enabled_errands = []
	deploy_errand_list = None if deploy_errands is None else deploy_errands.split(',')
	delete_errand_list = None if delete_errands is None else delete_errands.split(',')
	try:
		changes = opsmgr.get_changes(deploy_errand_list, delete_errand_list)
		if len(changes['product_changes']) == 0:
			print('Nothing to do', file=sys.stderr)
			return
		for p in changes['product_changes']:
			post_deploy = serialize_errands(p, 'post_deploy', 'post_deploy_errands')
			enabled_errands.extend(post_deploy)
			pre_delete = serialize_errands(p, 'pre_delete', 'pre_delete_errands')
			enabled_errands.extend(pre_delete)

	except:
		# Assume we're talking to a PCF version prior to 1.7
		# It does not support the get_changes APIs
		# But it also does not require us to pass in the list of errands
		# So this is perfectly fine
		pass
	body = '&'.join(enabled_errands)
	in_progress = None
	install_id = None
	while install_id is None:
		response = opsmgr.post('/api/installation?ignore_warnings=1', body, check=False)
		if response.status_code == 422 and "Install in progress" in response.json()["errors"]:
			if in_progress is None:
				print('Waiting for in-progress installation to complete', file=sys.stderr)
				in_progress = opsmgr.last_install()
			time.sleep(10)
			if opsmgr.install_exists(in_progress + 1):
				install_id = in_progress + 1
				break
			continue
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

@cli.command('version')
def version_cmd():
	version = opsmgr.get_version()
	print('.'.join([ str(x) for x in version ]))

if __name__ == '__main__':
	try:
		cli()
	except Exception as e:
		print(e, file=sys.stderr)
		sys.exit(1)
