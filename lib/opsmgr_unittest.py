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
import requests
import opsmgr
import sys
from contextlib import contextmanager
from StringIO import StringIO

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
		self.assertEquals(opsmgr.last_install(check=self.no_install_exists), 0)

	def test_correctly_handles_first_install(self):
		self.assertEquals(opsmgr.last_install(check=self.first_install_exists), 1)

	def test_correctly_handles_twenty_installs(self):
		self.assertEquals(opsmgr.last_install(check=self.twenty_installs_exist), 20)


@mock.patch('opsmgr.get')
class TestGetChanges(unittest.TestCase):

	def json_response(self, body):
		response = requests.Response()
		response.status_code = 200
		response.encoding = 'application/json'
		response.raw = StringIO(body)
		return response

	def test_default_errands(self, mock_get_changes):
		resp_not_found = requests.Response()
		resp_not_found.status_code = 404

		mock_get_changes.side_effect = [
			resp_not_found,
			self.json_response(json_deploy_products),
			self.json_response(json_staged_products),
			self.json_response(json_broker_one_manifest),
			self.json_response(json_tile_two_manifest)
		]

		product_changes = opsmgr.get_changes()

		changes = product_changes['product_changes']
		self.assertEquals(len(changes), 2)

		change_one = changes[0]
		self.assertEquals(change_one['action'], 'update')
		self.assertEquals(change_one['guid'], 'service-broker-one-9ed445129ddee5b24bff')

		change_one_errands = change_one['errands']
		self.assertEquals(len(change_one_errands), 1)
		self.assertEquals(change_one_errands[0]['name'], 'deploy-all')
		self.assertTrue(change_one_errands[0]['post_deploy'])

		change_two = changes[1]
		self.assertEquals(change_two['action'], 'update')
		self.assertEquals(change_two['guid'], 'tile-two-ed10ef2a821e0e810f2c')

		change_two_errands = change_two['errands']
		self.assertEquals(len(change_two_errands), 1)
		self.assertEquals(change_two_errands[0]['name'], 'deploy-all')
		self.assertTrue(change_two_errands[0]['post_deploy'])

	def test_custom_deploy_errands(self, mock_get_changes):
		resp_not_found = requests.Response()
		resp_not_found.status_code = 404

		mock_get_changes.side_effect = [
			resp_not_found,
			self.json_response(json_deploy_products),
			self.json_response(json_staged_products),
			self.json_response(json_broker_one_manifest),
			self.json_response(json_tile_two_manifest)
		]

		product_changes = opsmgr.get_changes(post_deploy_errands = ['deploy-all', 'configure-broker', 'missing'])

		changes = product_changes['product_changes']
		self.assertEquals(len(changes), 2)

		change_one = changes[0]
		self.assertEquals(change_one['guid'], 'service-broker-one-9ed445129ddee5b24bff')
		self.assertEquals(len(change_one['errands']), 1)

		change_two = changes[1]
		self.assertEquals(change_two['guid'], 'tile-two-ed10ef2a821e0e810f2c')
		change_two_errands = change_two['errands']
		self.assertEquals(len(change_two_errands), 2)
		self.assertEquals(change_two_errands[0]['name'], 'deploy-all')
		self.assertTrue(change_two_errands[0]['post_deploy'])
		self.assertEquals(change_two_errands[1]['name'], 'configure-broker')
		self.assertTrue(change_two_errands[1]['post_deploy'])



if __name__ == '__main__':
	unittest.main()


json_deploy_products = """
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

json_staged_products = """
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

json_broker_one_manifest = """
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

json_tile_two_manifest = """
{
    "manifest": {
        "jobs": [
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
