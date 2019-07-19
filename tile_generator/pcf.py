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
from .version import version_string


@click.group()
@click.version_option(version_string, '-v', '--version', message='%(prog)s version %(version)s')
@click.option('-t', '--target')
@click.option('-n', '--non-interactive', is_flag=True)
def cli(target, non_interactive):
	opsmgr.get_credentials(target, non_interactive)


@cli.command('ssh')
@click.argument('argv', nargs=-1)
@click.option('--skip-bosh-login', '-s', is_flag=True)
@click.option('--quiet', '-q', is_flag=True)
def ssh_cmd(argv, skip_bosh_login=False, quiet=False):
	opsmgr.ssh(command=' '.join(argv), login_to_bosh=not(skip_bosh_login), quiet=quiet)


@cli.command('reboot')
def reboot_cmd():
	opsmgr.ssh(command='sudo reboot now', login_to_bosh=False)
	opsmgr.unlock()


@cli.command('unlock')
def unlock_cmd():
	opsmgr.unlock()


@cli.command('products')
def products_cmd():
	products = opsmgr.get_products()
	for product in products:
		click.echo("- %s %s %s" % (product["name"], product["product_version"], "(installed)" if product["installed"] else ""))


@cli.command('changes')
def changes_cmd():
	changes = opsmgr.get_changes()
	if changes is None:
		click.echo('This command is only available for PCF 1.7 and beyond.', err=True)
		sys.exit(1)
	for p in changes['product_changes']:
		click.echo("%s %s" % (p['action'], p['guid']))
		for e in p['errands']:
			click.echo('- %s' % e['name'])


@cli.command('is-available')
@click.argument('product')
@click.argument('version', required=False)
def is_available_cmd(product, version):
	products = opsmgr.get_products()
	matches = [p for p in products if p['name'] == product and (version is None or p['product_version'] == version)]
	if len(matches) < 1:
		click.echo('No match found for product %s version %s' % (product, version), err=True)
		sys.exit(1)


@cli.command('is-installed')
@click.argument('product')
@click.argument('version', required=False)
def is_installed_cmd(product, version):
	products = opsmgr.get_products()
	matches = [p for p in products if p['name'] == product and (version is None or p['product_version'] == version) and p['installed']]
	if len(matches) < 1:
		click.echo('Product %s version %s is not installed' % (product, version), err=True)
		sys.exit(1)


@cli.command('configure')
@click.argument('product')
@click.argument('properties_file', required=False)
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
@click.argument('product', required=False)
def settings_cmd(product):
	settings = opsmgr.get('/api/installation_settings').json()
	if product is not None:
		settings = [ p for p in settings['products'] if p['identifier'] == product ]
		if len(settings) < 1:
			click.echo('No settings found for product %s' % product, err=True)
			sys.exit(1)
		settings = settings[0]
	click.echo(json.dumps(settings, indent=4))


@cli.command('cf-info')
def cf_info_cmd():
	cfinfo = opsmgr.get_cfinfo()
	for key in sorted(cfinfo):
		click.echo('- %s: %s' % (key, cfinfo[key]))


@cli.command('om')
def om_cmd():
	creds = opsmgr.get_credentials()
	click.echo('export OM_TARGET=%s' % creds['opsmgr']['url'])
	click.echo('export OM_USERNAME=%s' % creds['opsmgr']['username'])
	click.echo('export OM_PASSWORD=%s' % creds['opsmgr']['password'])


@cli.command('import')
@click.argument('tile')
def import_cmd(tile):
	opsmgr.upload('/api/products', tile)
	click.echo('- Tile %s imported successfully. You can run `pcf install` to load it.' % tile)


@cli.command('install')
@click.argument('product')
@click.argument('version')
def install_cmd(product, version):
	products = opsmgr.get_products()
	matches = [p for p in products if p['name'] == product and p['installed']]
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
					click.echo('- version already installed')
					return
		opsmgr.check_response(response)


@cli.command('uninstall')
@click.argument('product')
@click.argument('version', required=False)
def uninstall_cmd(product, version):
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [p for p in products if p['type'] == product]
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
	creds = opsmgr.get_credentials()
	with open(backup_file, 'rb') as f:
		payload = {'installation[file]': f, 'password': creds['opsmgr']['password']}
		opsmgr.post('/api/installation_asset_collection', f)


@cli.command('cleanup')
@click.argument('product')
def cleanup_cmd(product):
	#
	# Attempt 1 - Delete any uninstalled versions
	#
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [p for p in products if p['type'] == product]
	for match in matches:
		click.echo('- attempting to delete %s' % match['name'], err=True)
		opsmgr.delete('/api/installation_settings/products/' + match['guid'])
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [p for p in products if p['type'] == product]
	if len(matches) < 1:
		sys.exit(0)
	if len(matches) > 1:
		click.echo('- more than one match remains installed', err=True)
		sys.exit(1)
	#
	# Attempt 2 - Uninstall deployed version
	#
	match = matches[0]
	click.echo('- product was deployed, applying changes to uninstall it', err=True)
	apply_changes_cmd()
	opsmgr.delete('/api/products')
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [p for p in products if p['type'] == product]
	if len(matches) < 1:
		sys.exit(0)
	#
	# Attempt 3 - Re-deploy with errands disabled, then uninstall
	#
	match = matches[0]
	click.echo('- uninstall appears to have failed', err=True)
	click.echo('- re-deploying with disabled errands', err=True)
	opsmgr.disable_errands(product)
	apply_changes_cmd()
	click.echo('- uninstalling with disabled errands', err=True)
	opsmgr.delete('/api/installation_settings/products/' + match['guid'])
	apply_changes_cmd()
	opsmgr.delete('/api/products')
	products = opsmgr.get('/api/installation_settings/products').json()
	matches = [p for p in products if p['type'] == product]
	if len(matches) > 0:
		click.echo('- failed to uninstall', err=True)
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
				click.echo('Nothing to do', err=True)
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
				click.echo('Waiting for in-progress installation to complete', err=True)
				in_progress = opsmgr.last_install()
			time.sleep(10)
			if opsmgr.install_exists(in_progress + 1):
				install_id = in_progress + 1
				break
			continue
		elif response.status_code == 422:
			click.echo('- %d %s' % (response.status_code, response.request.url), err=True)
			try:
				errors = response.json()["errors"]
				click.echo('- ' + ('\n- '.join(json.dumps(errors, indent=4).splitlines())), err=True)
			except:
				click.echo(response.text, err=True)
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
@click.argument('install_id', required=False)
def logs_cmd(install_id=None):
	opsmgr.logs(install_id)


@cli.command('test-errand')
@click.argument('tile_repo')
@click.argument('errand_name')
def test_errand_cmd(tile_repo, errand_name):
	click.echo('test-errand is currently disabled while we work on improving it (issue #134)', err=True)
	sys.exit(1)
	rendered_errand = erb.render(errand_name, tile_repo)
	env = os.environ
	env['PACKAGE_PATH'] = os.path.join(tile_repo, 'release/blobs')
	os.execlpe('bash', 'bash', rendered_errand, env)


@cli.command('target')
@click.option('--org', '-o', default=None)
@click.option('--space', '-s', default=None)
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
		login += ['-o', org]
	if space is not None:
		login += ['-s', space]
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
		click.echo('Unsupported request type: %s' % request, err=True)
		sys.exit(1)
	click.echo(json.dumps(response.json(), indent=2))


@cli.command('errands')
@click.argument('product')
def errands_cmd(product):
	products = opsmgr.get('/api/v0/staged/products').json()
	guid = [p for p in products if p['type'] == product][0]['guid']
	errands = opsmgr.get('/api/v0/staged/products/' + guid + '/errands').json()['errands']
	click.echo(json.dumps(errands, indent=4))


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
		opsmgr.put_json('/api/v0/staged/products/' + guid + '/errands', {'errands': errands})


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
		opsmgr.put_json('/api/v0/staged/products/' + guid + '/errands', {'errands': errands})


@cli.command('version')
def version_cmd():
	version = opsmgr.get_version()
	click.echo('.'.join([str(x) for x in version]))


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
	click.echo(yaml.safe_dump(creds, default_flow_style=False, explicit_start=True), nl=False)


@cli.command('bosh-env')
def bosh_env_cmd():
	director_creds = opsmgr.get('/api/v0/deployed/director/credentials/director_credentials').json()
	director_manifest = opsmgr.get('/api/v0/deployed/director/manifest').json()

	# PCF 2.2 and earlier has 'jobs' array at top level, while
	# PCF 2.3 and later has 'instance_groups'
	director_address = director_manifest.get('instance_groups', director_manifest.get('jobs'))[0]['properties']['director']['address']

	click.echo('BOSH_ENVIRONMENT="%s"' % director_address)
	click.echo('BOSH_CA_CERT="/var/tempest/workspaces/default/root_ca_certificate"')
	click.echo('BOSH USERNAME=%s' % director_creds['credential']['value']['identity'])
	click.echo('BOSH PASSWORD=%s' % director_creds['credential']['value']['password'])


@cli.command('password')
def password():
	creds = opsmgr.get_credentials()
	click.echo(creds['opsmgr']['password'])


@cli.command('history')
def history_cmd():
	history = opsmgr.get_history()
	click.echo(json.dumps(history, indent=4))


@cli.command('upload-stemcell')
@click.argument('stemcell-file')
def upload_stemcell_cmd(stemcell_file):
	opsmgr.post('/api/v0/stemcells', None, files={'stemcell[file]': open(stemcell_file, 'rb')})
	click.echo('stemcell uploaded')


@cli.command('stemcells')
def stemcells_cmd():
	stemcells = opsmgr.get_stemcells()
	click.echo(json.dumps(stemcells, indent=4))


def main():
	try:
		cli()
	except Exception as e:
		click.echo(e, err=True)
		sys.exit(1)


if __name__ == '__main__':
	main()
