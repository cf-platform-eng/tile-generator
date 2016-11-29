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
import unittest
import mock
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


def build_json_response(body):
	response = requests.Response()
	response.status_code = 200
	response.encoding = 'application/json'
	response.raw = BytesIO(body)
	return response


@mock.patch('tile_generator.opsmgr.get')
class TestGetChanges17(unittest.TestCase):
	def test_custom_deploy_errands(self, mock_get):
		resp_not_found = requests.Response()
		resp_not_found.status_code = 404

		mock_get.side_effect = [
			build_json_response(api_responses_1_7['diagnostic_report']),
			build_json_response(api_responses_1_7['deployed_products']),
			build_json_response(api_responses_1_7['staged_products']),
			build_json_response(api_responses_1_7['broker_one_manifest']),
			build_json_response(api_responses_1_7['tile_two_manifest']),
			build_json_response(api_responses_1_7['deleting_manifest']),
		]

		product_changes = opsmgr.get_changes(
			product='tile-two',
			deploy_errands=['deploy-all']
		)

		changes = product_changes['product_changes']
		self.assertEqual(len(changes), 1)

		update = changes[0]
		self.assertEqual(update['action'], 'update')
		self.assertEqual(update['guid'], 'tile-two-ed10ef2a821e0e810f2c')

	def test_custom_delete_errands(self, mock_get):
		resp_not_found = requests.Response()
		resp_not_found.status_code = 404

		mock_get.side_effect = [
			build_json_response(api_responses_1_7['diagnostic_report']),
			build_json_response(api_responses_1_7['deployed_products']),
			build_json_response(api_responses_1_7['staged_products']),
			build_json_response(api_responses_1_7['broker_one_manifest']),
			build_json_response(api_responses_1_7['tile_two_manifest']),
			build_json_response(api_responses_1_7['deleting_manifest']),
		]

		product_changes = opsmgr.get_changes(
			deploy_errands=['deploy-all'],
			delete_errands=['delete-all', 'delete-cleanup']
		)

		changes = product_changes['product_changes']
		self.assertEqual(len(changes), 3)

		delete = changes[0]
		self.assertEqual(delete['action'], 'delete')
		self.assertEqual(delete['guid'], 'deleting-ecb2884a79cf44f5849b')

		delete_errands = delete['errands']
		self.assertEqual(len(delete_errands), 2)
		self.assertEqual(delete_errands[0]['name'], 'delete-all')
		self.assertTrue(delete_errands[0]['pre_delete'])
		self.assertEqual(delete_errands[1]['name'], 'delete-cleanup')
		self.assertTrue(delete_errands[1]['pre_delete'])

@mock.patch('tile_generator.opsmgr.get')
class TestGetChanges18(unittest.TestCase):
	def test_default_install_errands(self, mock_get):
		mock_get.side_effect = [
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_install'])
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
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_install'])
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
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_update'])
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
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_update'])
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
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_delete'])
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
			build_json_response(api_responses_1_8['diagnostic_report']),
			build_json_response(api_responses_1_8['pending_changes_delete'])
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

if __name__ == '__main__':
	unittest.main()
