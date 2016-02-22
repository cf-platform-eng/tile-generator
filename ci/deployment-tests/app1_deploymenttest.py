import unittest
import json
import sys
import os
import requests

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(os.path.join(os.path.join(PATH, '..'), '..'), 'lib'))
import opsmgr

class VerifyApp1(unittest.TestCase):

	def setUp(self):
		self.cfinfo = opsmgr.get_cfinfo()
		self.hostname = 'app1.' + self.cfinfo['apps_domain']
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
		self.assertEqual(env.get('COUNTRY'), 'US')

	def test_receives_expected_services(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_services = json.loads(env.get('VCAP_SERVICES'))

	def test_has_versioned_name(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_application = json.loads(env.get('VCAP_APPLICATION'))
		name = vcap_application.get('application_name')
		self.assertTrue(name.startswith('app1-'))

	def test_is_in_correct_space(self):
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/env', headers=headers)
		response.raise_for_status()
		env = response.json()
		vcap_application = json.loads(env.get('VCAP_APPLICATION'))
		space= vcap_application.get('space_name')
		self.assertEquals(space, 'test-tile-space')

if __name__ == '__main__':
	unittest.main()
