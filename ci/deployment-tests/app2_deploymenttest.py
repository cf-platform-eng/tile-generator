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
import json
import sys
import os
import requests
from tile_generator import opsmgr

class VerifyApp2(unittest.TestCase):

	def setUp(self):
		self.cfinfo = opsmgr.get_cfinfo()
		self.hostname = 'tg-test-app2-hostname.' + self.cfinfo['apps_domain']
		self.url = 'http://' + self.hostname

	def test_responds_to_hello(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/hello', headers=headers)
		response.raise_for_status()

	def test_receives_custom_properties(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		self.assertEqual(env.get('AUTHOR'), 'Tile Ninja')
		self.assertEqual(env.get('CUSTOMER_NAME'), "Jimmy's Johnnys")
		self.assertEqual(env.get('STREET_ADDRESS'), 'Cartaway Alley')
		self.assertEqual(env.get('CITY'), 'New Jersey')
		self.assertEqual(env.get('ZIP_CODE'), '90310')
		self.assertEqual(env.get('COUNTRY'), 'country_us')

	def test_receives_link_hosts(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		self.assertTrue(env.get('REDIS_HOST') is not None)
		self.assertTrue(env.get('REDIS_HOSTS') is not None)
		self.assertTrue(env.get('NATS_HOST') is not None)
		self.assertTrue(env.get('NATS_HOSTS') is not None)

	def test_receives_link_properties(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		self.assertIsNotNone(json.loads(env.get('REDIS_PROPERTIES')))
		self.assertIsNotNone(json.loads(env.get('NATS_PROPERTIES')))

	def test_receives_expected_services(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_services = json.loads(env.get('VCAP_SERVICES'))
		broker1_service = vcap_services.get('tg_test_broker1-service', None)
		self.assertTrue(broker1_service is not None)
		self.assertEquals(len(broker1_service), 1)
		self.assertEquals(broker1_service[0].get('plan'), 'first-plan')
	
	def test_has_versioned_name(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_application = json.loads(env.get('VCAP_APPLICATION'))
		name = vcap_application.get('application_name')
		self.assertTrue(name.startswith('tg_test_app2-'))

	def test_is_in_correct_space(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_application = json.loads(env.get('VCAP_APPLICATION'))
		space= vcap_application.get('space_name')
		self.assertEquals(space, 'test-tile-space')

	def test_receives_expected_admin_credentials(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		user = env.get('CF_ADMIN_USER')
		username = env.get('CF_ADMIN_USERNAME')
		password = env.get('CF_ADMIN_PASSWORD')
		self.assertEquals(user, username)
		self.assertEquals(user, 'system_services')
		self.assertFalse(password is None)

if __name__ == '__main__':
	unittest.main()
