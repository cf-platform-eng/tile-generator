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

class VerifyApp4Proxy(unittest.TestCase):

	def getEnv(self, url):
		headers = { 'Accept': 'application/json' }
		response = requests.get(url + '/env', headers=headers)
		response.raise_for_status()
		return response.json()

	def setUp(self):
		self.cfinfo = opsmgr.get_cfinfo()
		self.proxy = 'http://tg_test_app1.' + self.cfinfo['apps_domain']
		self.env = self.getEnv(self.proxy)
		self.host = self.env.get('DOCKER_TCP_HOST')
		if self.host is not None:
			self.url = self.proxy + '/proxy?url=http://' + self.host + ':8080'

	def skipIfNoHost(self):
		if self.host is None:
			self.skipTest("Proxy did not receive app4 host address")

	def test_responds_to_hello(self):
		self.skipIfNoHost()
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/hello', headers=headers)
		response.raise_for_status()

class VerifyApp4(unittest.TestCase):

	def setUp(self):
		self.cfinfo = opsmgr.get_cfinfo()
		self.hostname = 'my_route_tg_test_app4.' + self.cfinfo['system_domain']
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

	def test_receives_expected_collection(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		example_collection = json.loads(env.get('EXAMPLE_COLLECTION'))
		self.assertTrue(isinstance(example_collection, list))
		self.assertEquals(len(example_collection), 2)

	def test_receives_expected_selector(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		example_selector = json.loads(env.get('EXAMPLE_SELECTOR'))
		self.assertTrue(isinstance(example_selector, dict))
		self.assertEquals(example_selector['value'], 'Filet Mignon')
	#	self.assertEquals(example_selector['selected_option']['rarity_dropdown'], 'medium')

if __name__ == '__main__':
	unittest.main()
