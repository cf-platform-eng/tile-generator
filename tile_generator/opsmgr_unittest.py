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


import unittest
import mock
import json
import requests
from . import opsmgr
import sys
from contextlib import contextmanager
from io import StringIO, BytesIO

@contextmanager
def capture_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class TestInstallTriangulation(unittest.TestCase):

	def no_install_exists(self, id):
		return False

	def first_install_exists(self, id):
		return id == 1

	def twenty_installs_exist(self, id):
		return id > 0 and id <= 20

	def only_higher_installs_exist(self, id):
		return id > 10 and id <= 20

	def test_correctly_handles_no_installs(self):
		self.assertEqual(opsmgr.last_install(check=self.no_install_exists), 0)

	def test_correctly_handles_first_install(self):
		self.assertEqual(opsmgr.last_install(check=self.first_install_exists), 1)

	def test_correctly_handles_twenty_installs(self):
		self.assertEqual(opsmgr.last_install(check=self.twenty_installs_exist), 20)


def build_response(body, encoding='application/json', status_code=200):
	response = requests.Response()
	response.status_code = status_code
	response.encoding =encoding
	response.raw = BytesIO(body)
	response.request = requests.Request()
	response.request.url = 'https://example.com/'
	return response

class TestCheckResponse(unittest.TestCase):
	def test_noop_when_check_is_false(self):
		self.assertIsNone(opsmgr.check_response(None, False))

	def test_noop_when_response_ok(self):
		self.assertIsNone(opsmgr.check_response(build_response(None), True))

	def test_raise_exception_when_response_not_ok(self):
		with self.assertRaises(Exception):
			opsmgr.check_response(build_response(None, status_code=500),True)

	def test_exceptions_contains_json(self):
		try:
			opsmgr.check_response(build_response(bytes(json.dumps("body"), encoding='utf-8'), status_code=500), True)
		except Exception as e:
			self.assertIn('body', str(e))

	def test_exceptions_contains_non_json_body(self):
		try:
			opsmgr.check_response(build_response(b"body", encoding='text/plain', status_code=500), True)
		except Exception as e:
			self.assertIn('body', str(e))



@mock.patch('tile_generator.opsmgr.get')
class TestGetChanges18(unittest.TestCase):
	def test_default_install_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_install'])
		]

		product_changes = opsmgr.get_changes()
		changes = product_changes['product_changes']
		self.assertEqual(len(changes), 1)

		install = changes[0]
		self.assertEqual(install['guid'], 'service-broker-one-8a46337545b088152272')
		self.assertEqual(install['action'], 'install')

		install_errands = install['errands']
		self.assertEqual(len(install_errands), 2)
		self.assertEqual(install_errands[0]['name'], 'deploy-all')
		self.assertTrue(install_errands[0]['post_deploy'])
		self.assertEqual(install_errands[1]['name'], 'config-broker')
		self.assertTrue(install_errands[1]['post_deploy'])

	def test_custom_install_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_install'])
		]

		product_changes = opsmgr.get_changes(['deploy-all', 'config-broker'])
		changes = product_changes['product_changes']

		self.assertEqual(len(changes), 1)

		install = changes[0]
		self.assertEqual(install['guid'], 'service-broker-one-8a46337545b088152272')
		self.assertEqual(install['action'], 'install')

		install_errands = install['errands']
		self.assertEqual(len(install_errands), 2)
		self.assertEqual(install_errands[0]['name'], 'deploy-all')
		self.assertTrue(install_errands[0]['post_deploy'])
		self.assertEqual(install_errands[1]['name'], 'config-broker')
		self.assertTrue(install_errands[1]['post_deploy'])

	def test_default_update_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_update'])
		]

		product_changes = opsmgr.get_changes()
		changes = product_changes['product_changes']

		self.assertEqual(len(changes), 1)

		install = changes[0]
		self.assertEqual(install['guid'], 'service-broker-two-e8e9996bf23a455fbee6')
		self.assertEqual(install['action'], 'update')

		install_errands = install['errands']
		self.assertEqual(len(install_errands), 2)
		self.assertEqual(install_errands[0]['name'], 'deploy-all')
		self.assertTrue(install_errands[0]['post_deploy'])
		self.assertEqual(install_errands[1]['name'], 'config-broker')
		self.assertTrue(install_errands[1]['post_deploy'])

	def test_custom_update_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_update'])
		]

		product_changes = opsmgr.get_changes(['deploy-all', 'config-broker'])
		changes = product_changes['product_changes']

		self.assertEqual(len(changes), 1)

		install = changes[0]
		self.assertEqual(install['guid'], 'service-broker-two-e8e9996bf23a455fbee6')
		self.assertEqual(install['action'], 'update')

		install_errands = install['errands']
		self.assertEqual(len(install_errands), 2)
		self.assertEqual(install_errands[0]['name'], 'deploy-all')
		self.assertTrue(install_errands[0]['post_deploy'])
		self.assertEqual(install_errands[1]['name'], 'config-broker')
		self.assertTrue(install_errands[1]['post_deploy'])

	def test_default_delete_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_delete'])
		]

		product_changes = opsmgr.get_changes()
		changes = product_changes['product_changes']

		self.assertEqual(len(changes), 2)

		delete_one = changes[0]
		self.assertEqual(delete_one['guid'], 'key-value-tile-ce5a27ce8a93145ed200')
		self.assertEqual(delete_one['action'], 'delete')

		delete_one_errands = delete_one['errands']
		self.assertEqual(len(delete_one_errands), 1)
		self.assertEqual(delete_one_errands[0]['name'], 'delete-all')
		self.assertTrue(delete_one_errands[0]['pre_delete'])

		delete_two = changes[1]
		self.assertEqual(delete_two['guid'], 'db-on-demand-c8ace318b641342d8420')
		self.assertEqual(delete_two['action'], 'delete')

		delete_two_errands = delete_two['errands']
		self.assertEqual(len(delete_two_errands), 2)
		self.assertEqual(delete_two_errands[0]['name'], 'delete_subdeployments_on_demand_service_broker')
		self.assertTrue(delete_two_errands[0]['pre_delete'])
		self.assertEqual(delete_two_errands[1]['name'], 'unregister_on_demand_service_broker')
		self.assertTrue(delete_two_errands[1]['pre_delete'])

	def test_custom_delete_errands(self, mock_get):
		mock_get.side_effect = [
			build_response(api_responses_1_8['pending_changes_delete'])
		]

		product_changes = opsmgr.get_changes(delete_errands = [
			'delete_subdeployments_on_demand_service_broker',
			'unregister_on_demand_service_broker'
		])

		changes = product_changes['product_changes']

		self.assertEqual(len(changes), 2)

		delete_one = changes[0]
		self.assertEqual(delete_one['guid'], 'key-value-tile-ce5a27ce8a93145ed200')
		self.assertEqual(delete_one['action'], 'delete')

		delete_one_errands = delete_one['errands']
		self.assertEqual(len(delete_one_errands), 0)

		delete_two = changes[1]
		self.assertEqual(delete_two['guid'], 'db-on-demand-c8ace318b641342d8420')
		self.assertEqual(delete_two['action'], 'delete')

		delete_two_errands = delete_two['errands']
		self.assertEqual(len(delete_two_errands), 2)
		self.assertEqual(delete_two_errands[0]['name'], 'delete_subdeployments_on_demand_service_broker')
		self.assertTrue(delete_two_errands[0]['pre_delete'])
		self.assertEqual(delete_two_errands[1]['name'], 'unregister_on_demand_service_broker')
		self.assertTrue(delete_two_errands[1]['pre_delete'])


api_responses_1_7 = {}
api_responses_1_7['diagnostic_report'] = b"""
{
	"versions": {
		"release_version": "1.7.14"
	}
}
"""
api_responses_1_7['deployed_products'] = b"""
[
    {
        "guid": "service-broker-one-9ed445129ddee5b24bff",
        "installation_name": "service-broker-one-9ed445129ddee5b24bff",
        "type": "service-broker-one"
    },
    {
        "guid": "tile-two-ed10ef2a821e0e810f2c",
        "installation_name": "tile-two-ed10ef2a821e0e810f2c",
        "type": "tile-two"
    },
    {
        "guid": "deleting-ecb2884a79cf44f5849b",
        "installation_name": "tile-two-ecb2884a79cf44f5849b",
        "type": "tile-two"
    }
]
"""
api_responses_1_7['staged_products'] = b"""
[
    {
        "guid": "service-broker-one-9ed445129ddee5b24bff",
        "installation_name": "service-broker-one-9ed445129ddee5b24bff",
        "type": "service-broker-one"
    },
    {
        "guid": "tile-two-ed10ef2a821e0e810f2c",
        "installation_name": "tile-two-ed10ef2a821e0e810f2c",
        "type": "tile-two"
    }
]
"""
api_responses_1_7['broker_one_manifest'] = b"""
{
    "manifest": {
        "jobs": [
            {
                "templates": [
                    {
                        "release": "service-broker-one",
                        "name": "deploy-all"
                    }
                ],
                "resource_pool": "deploy-all",
                "properties": {},
                "name": "deploy-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": []
            },
            {
                "templates": [
                    {
                        "release": "service-broker-one",
                        "name": "delete-all"
                    }
                ],
                "resource_pool": "delete-all",
                "properties": {},
                "name": "delete-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": [
                    {
                        "default": [
                            "dns",
                            "gateway"
                        ],
                        "name": "default"
                    }
                ]
            }
        ],
        "name": "service-broker-one-9ed445129ddee5b24bff",
        "releases": [
            {
                "version": "0.1.11",
                "name": "service-broker-one"
            }
        ],
        "compilation": {},
        "update": {},
        "resource_pools": [],
        "director_uuid": "ignore",
        "networks": [],
        "disk_pools": []
    }
}
"""
api_responses_1_7['tile_two_manifest'] = b"""
{
    "manifest": {
        "jobs": [
            {
                "templates": [
                    {
                        "release": "tile-two",
                        "name": "deploy-all"
                    }
                ],
                "resource_pool": "deploy-all",
                "properties": {},
                "name": "deploy-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": [
                    {
                        "default": [
                            "dns",
                            "gateway"
                        ],
                        "name": "default"
                    }
                ]
            },
            {
                "templates": [
                    {
                        "release": "tile-two",
                        "name": "configure-broker"
                    }
                ],
                "resource_pool": "configure-broker",
                "properties": {},
                "name": "configure-broker",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": []
            },
            {
                "templates": [
                    {
                        "release": "tile-two",
                        "name": "delete-all"
                    }
                ],
                "resource_pool": "delete-all",
                "properties": {},
                "name": "delete-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": []
            }
        ],
        "name": "tile-two-ed10ef2a821e0e810f2c",
        "releases": [
            {
                "version": "0.0.171",
                "name": "tile-two"
            },
            {
                "version": "102",
                "name": "tile-two"
            }
        ],
        "compilation": {},
        "update": {
            "update_watch_time": "30000-300000",
            "canary_watch_time": "30000-300000",
            "max_errors": 2,
            "max_in_flight": 1,
            "serial": true,
            "canaries": 1
        },
        "resource_pools": [],
        "director_uuid": "ignore",
        "networks": [],
        "disk_pools": []
    }
}
"""
api_responses_1_7['deleting_manifest'] = b"""
{
    "manifest": {
        "jobs": [
            {
                "templates": [
                    {
                        "release": "deleting",
                        "name": "delete-cleanup"
                    }
                ],
                "resource_pool": "delete-cleanup",
                "properties": {},
                "name": "delete-cleanup",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": []
            },
            {
                "templates": [
                    {
                        "release": "deleting",
                        "name": "deploy-all"
                    }
                ],
                "resource_pool": "deploy-all",
                "properties": {},
                "name": "deploy-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": [
                    {
                        "default": [
                            "dns",
                            "gateway"
                        ],
                        "name": "default"
                    }
                ]
            },
            {
                "templates": [
                    {
                        "release": "deleting",
                        "name": "delete-all"
                    }
                ],
                "resource_pool": "delete-all",
                "properties": {},
                "name": "delete-all",
                "update": {
                    "max_in_flight": 1
                },
                "lifecycle": "errand",
                "instances": 1,
                "networks": []
            }
        ],
        "name": "deleting-ecb2884a79cf44f5849b",
        "releases": [
            {
                "version": "0.0.171",
                "name": "deleting"
            },
            {
                "version": "102",
                "name": "deleting"
            }
        ],
        "compilation": {},
        "update": {
            "update_watch_time": "30000-300000",
            "canary_watch_time": "30000-300000",
            "max_errors": 2,
            "max_in_flight": 1,
            "serial": true,
            "canaries": 1
        },
        "resource_pools": [],
        "director_uuid": "ignore",
        "networks": [],
        "disk_pools": []
    }
}
"""

api_responses_1_8 = {}
api_responses_1_8['diagnostic_report'] = b"""
{
	"versions": {
		"release_version": "1.8.4"
	}
}
"""
api_responses_1_8['pending_changes_install'] = b"""
{
    "product_changes": [
        {
            "action": "install",
            "guid": "service-broker-one-8a46337545b088152272",
            "errands": [
                {
                    "name": "deploy-all",
                    "post_deploy": true
                },
                {
                    "name": "config-broker",
                    "post_deploy": true
                }
            ]
        }
    ]
}
"""
api_responses_1_8['pending_changes_update'] = b"""
{
    "product_changes": [
        {
            "action": "update",
            "guid": "service-broker-two-e8e9996bf23a455fbee6",
            "errands": [
                {
                    "name": "deploy-all",
                    "post_deploy": true
                },
                {
                    "name": "config-broker",
                    "post_deploy": true
                }
            ]
        }
    ]
}
"""
api_responses_1_8['pending_changes_delete'] = b"""
{
    "product_changes": [
        {
            "action": "delete",
            "guid": "key-value-tile-ce5a27ce8a93145ed200",
            "errands": [
                {
                    "pre_delete": true,
                    "name": "delete-all"
                }
            ]
        },
        {
            "action": "delete",
            "guid": "db-on-demand-c8ace318b641342d8420",
            "errands": [
                {
                    "pre_delete": true,
                    "name": "delete_subdeployments_on_demand_service_broker"
                },
                {
                    "pre_delete": true,
                    "name": "unregister_on_demand_service_broker"
                }
            ]
        }
    ]
}
"""

def v0_get(responses):
	def get(url, stream=False, check=True):
		if url not in responses:
			return build_response(b'{"status":404,"error":"Not Found"}', status_code=404)
		return build_response(responses[url])
	return get

@mock.patch('tile_generator.opsmgr.get')
class TestV0ProductsAndCfInfo(unittest.TestCase):
	def test_get_cfinfo_reads_properties_and_credentials(self, mock_get):
		mock_get.side_effect = v0_get(api_responses_v0)
		cfinfo = opsmgr.get_cfinfo()
		self.assertEqual(cfinfo['system_domain'], 'sys.example.com')
		self.assertEqual(cfinfo['apps_domain'], 'apps.example.com')
		self.assertEqual(cfinfo['admin_username'], 'admin')
		self.assertEqual(cfinfo['admin_password'], 'admin-secret')
		self.assertEqual(cfinfo['system_services_username'], 'system_services')
		self.assertEqual(cfinfo['system_services_password'], 'services-secret')
		self.assertEqual(cfinfo['schema_version'], '11.0')

	def test_get_cfinfo_requires_cf(self, mock_get):
		mock_get.side_effect = v0_get(dict(api_responses_v0, **{'/api/v0/staged/products': b'[]'}))
		with self.assertRaises(Exception) as e:
			opsmgr.get_cfinfo()
		self.assertIn('Elastic Runtime is not installed', str(e.exception))

	def test_get_products_merges_staged_and_available(self, mock_get):
		mock_get.side_effect = v0_get(api_responses_v0)
		products = { (p['name'], p['product_version']): p for p in opsmgr.get_products() }
		self.assertTrue(products[('cf', '10.3.7')]['installed'])
		self.assertEqual(products[('cf', '10.3.7')]['guid'], 'cf-36f9d85a723246da59ef')
		self.assertTrue(products[('test-tile', '1.0.0')]['installed'])
		self.assertFalse(products[('test-tile', '1.1.0')]['installed'])
		self.assertEqual(len(products), 4)

@mock.patch('tile_generator.opsmgr.put_json')
@mock.patch('tile_generator.opsmgr.patch_json')
@mock.patch('tile_generator.opsmgr.get')
class TestV0Configure(unittest.TestCase):
	product_url = '/api/v0/staged/products/test-tile-0123456789abcdef0123'

	def test_uses_cf_stemcell(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja'}, skip_validation=True)
		mock_patch.assert_called_once_with('/api/v0/stemcell_associations', { 'products': [ {
			'guid': 'test-tile-0123456789abcdef0123',
			'staged_stemcells': [ {
				'name': 'bosh-warden-boshlite-ubuntu-jammy-go_agent',
				'os': 'ubuntu-jammy',
				'version': '1.9041',
				'variant': ['esm'],
			} ],
		} ] })

	def test_strict_keeps_product_stemcell(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		opsmgr.configure('test-tile', {'author': 'Tile Ninja'}, strict=True, skip_validation=True)
		mock_patch.assert_not_called()

	def test_sets_networks_azs_and_properties(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja', 'jobs': {'redis': {'maxmemory': '1gb'}}}, skip_validation=True)
		mock_put.assert_any_call(self.product_url + '/networks_and_azs', { 'networks_and_azs': {
			'singleton_availability_zone': { 'name': 'null' },
			'other_availability_zones': [ { 'name': 'null' } ],
			'network': { 'name': 'network' },
		} })
		mock_put.assert_any_call(self.product_url + '/properties', { 'properties': {
			'.properties.author': { 'value': 'Tile Ninja' },
			'.redis.maxmemory': '1gb',
		} })

	def test_network_option_overrides_default(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja'}, skip_validation=True, network='other-network')
		payload = [ c.args[1] for c in mock_put.call_args_list if c.args[0].endswith('/networks_and_azs') ][0]
		self.assertEqual(payload['networks_and_azs']['network'], { 'name': 'other-network' })

	def test_skips_networks_and_azs_without_azs(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(dict(api_responses_v0, **{'/api/v0/staged/director/availability_zones': b'{"availability_zones": []}'}))
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja'}, skip_validation=True)
		self.assertEqual([ c.args[0] for c in mock_put.call_args_list ], [ self.product_url + '/properties' ])

	def test_reports_missing_required_properties(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			with self.assertRaises(Exception) as e:
				opsmgr.configure('test-tile', {})
		message = str(e.exception)
		self.assertIn('- author', message)
		self.assertIn('- jobs.redis.password', message)
		self.assertNotIn('nickname', message) # optional
		self.assertNotIn('internal_id', message) # not configurable
		self.assertNotIn('app_credentials', message) # generated
		self.assertNotIn('custom_url', message) # option of an unselected selector
		mock_put.assert_not_called()

	def test_job_properties_satisfy_validation(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja', 'jobs': {'redis': {'password': 'x'}}})
		mock_put.assert_any_call(self.product_url + '/properties', { 'properties': {
			'.properties.author': { 'value': 'Tile Ninja' },
			'.redis.password': 'x',
		} })

	def test_skip_validation(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with capture_output():
			opsmgr.configure('test-tile', {}, skip_validation=True)
		mock_put.assert_any_call(self.product_url + '/properties', { 'properties': {} })

	def test_resource_config_uses_job_guid(self, mock_get, mock_patch, mock_put):
		resource_config_url = self.product_url + '/jobs/redis-0123456789abcdef0123/resource_config'
		mock_get.side_effect = v0_get(dict(api_responses_v0, **{resource_config_url: b'{"instances": 1, "instance_type": {"id": "automatic"}}'}))
		with capture_output():
			opsmgr.configure('test-tile', {'author': 'Tile Ninja', 'jobs': {'redis': {'resource_config': {'instances': 3}}}}, skip_validation=True)
		mock_put.assert_any_call(resource_config_url, {'instances': 3, 'instance_type': {'id': 'automatic'}})

	def test_requires_staged_product(self, mock_get, mock_patch, mock_put):
		mock_get.side_effect = v0_get(api_responses_v0)
		with self.assertRaises(Exception) as e:
			opsmgr.configure('missing-tile', {})
		self.assertIn('Product missing-tile does not appear to be installed', str(e.exception))


# Shapes captured from Ops Manager 11.0 (secrets replaced)
api_responses_v0 = {}
api_responses_v0['/api/v0/info'] = b'{"info":{"version":"11.0","locked":false,"setup_complete":true}}'
api_responses_v0['/api/v0/staged/products'] = b"""[
	{"installation_name": "p-bosh-0123456789abcdef0123", "guid": "p-bosh-0123456789abcdef0123", "type": "p-bosh", "product_version": "11.0.0-build.447", "label": "BOSH Director"},
	{"installation_name": "cf-36f9d85a723246da59ef", "guid": "cf-36f9d85a723246da59ef", "type": "cf", "product_version": "10.3.7", "label": "Small Footprint Elastic Application Runtime"},
	{"installation_name": "test-tile-0123456789abcdef0123", "guid": "test-tile-0123456789abcdef0123", "type": "test-tile", "product_version": "1.0.0", "label": "Test Tile"}
]"""
api_responses_v0['/api/products'] = b"""[
	{"name": "cf", "product_version": "10.3.7"},
	{"name": "test-tile", "product_version": "1.0.0"},
	{"name": "test-tile", "product_version": "1.1.0"}
]"""
api_responses_v0['/api/v0/staged/products/cf-36f9d85a723246da59ef/properties'] = b"""{"properties": {
	".cloud_controller.system_domain": {"type": "wildcard_domain", "configurable": true, "credential": false, "value": "sys.example.com", "optional": false},
	".cloud_controller.apps_domain": {"type": "wildcard_domain", "configurable": true, "credential": false, "value": "apps.example.com", "optional": false}
}}"""
api_responses_v0['/api/v0/deployed/products/cf-36f9d85a723246da59ef/credentials/.uaa.admin_credentials'] = b'{"credential": {"type": "simple_credentials", "value": {"identity": "admin", "password": "admin-secret"}}}'
api_responses_v0['/api/v0/deployed/products/cf-36f9d85a723246da59ef/credentials/.uaa.system_services_credentials'] = b'{"credential": {"type": "simple_credentials", "value": {"identity": "system_services", "password": "services-secret"}}}'
api_responses_v0['/api/v0/stemcell_associations'] = b"""{"products": [
	{"guid": "cf-36f9d85a723246da59ef", "identifier": "cf", "staged_stemcells": [{"label": "ubuntu-jammy 1.9041", "name": "bosh-warden-boshlite-ubuntu-jammy-go_agent", "os": "ubuntu-jammy", "version": "1.9041", "variant": ["esm"]}]},
	{"guid": "test-tile-0123456789abcdef0123", "identifier": "test-tile", "staged_stemcells": [{"label": "ubuntu-jammy 1.1390", "name": "bosh-warden-boshlite-ubuntu-jammy-go_agent", "os": "ubuntu-jammy", "version": "1.1390", "variant": []}]}
]}"""
api_responses_v0['/api/v0/staged/director/availability_zones'] = b'{"availability_zones": [{"name": "null", "guid": "null-az", "iaas_configuration_guid": "8845f75e1b193290b705"}]}'
api_responses_v0['/api/v0/staged/director/networks'] = b'{"icmp_checks_enabled": false, "networks": [{"guid": "1234", "name": "network", "subnets": []}]}'
api_responses_v0['/api/v0/staged/products/test-tile-0123456789abcdef0123/properties'] = b"""{"properties": {
	".properties.author": {"type": "string", "configurable": true, "credential": false, "value": null, "optional": false},
	".properties.nickname": {"type": "string", "configurable": true, "credential": false, "value": null, "optional": true},
	".properties.internal_id": {"type": "string", "configurable": false, "credential": false, "value": null, "optional": false},
	".properties.url_source": {"type": "selector", "configurable": true, "credential": false, "value": "Default", "optional": false, "selected_option": "default"},
	".properties.url_source.custom.custom_url": {"type": "string", "configurable": true, "credential": false, "value": null, "optional": false},
	".redis.password": {"type": "secret", "configurable": true, "credential": true, "value": null, "optional": false},
	".redis.app_credentials": {"type": "simple_credentials", "configurable": true, "credential": true, "value": null, "optional": false},
	".redis.maxmemory": {"type": "string", "configurable": true, "credential": false, "value": "512mb", "optional": false}
}}"""
api_responses_v0['/api/v0/staged/products/test-tile-0123456789abcdef0123/jobs'] = b'{"jobs": [{"name": "redis", "guid": "redis-0123456789abcdef0123", "label": "Redis"}]}'

if __name__ == '__main__':
	unittest.main()
