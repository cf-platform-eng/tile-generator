import unittest
import json
import sys
import os
import requests

PATH = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(os.path.join(os.path.join(PATH, '..'), '..'), 'lib'))
import opsmgr

class VerifyApp4(unittest.TestCase):

	def getEnv(self, url):
		headers = { 'Accept': 'application/json' }
		response = requests.get(url + '/env', headers=headers)
		response.raise_for_status()
		return response.json()

	def setUp(self):
		self.cfinfo = opsmgr.get_cfinfo()
		self.proxy = 'http://app1.' + self.cfinfo['apps_domain']
		self.env = self.getEnv(self.proxy)
		self.host = self.env.get('APP4_HOST')
		if self.host is not None:
			self.url = self.proxy + '/proxy?url=http://' + self.host + ':8080'

	def skipIfNoHost(self):
		if self.host is None:
			self.skipTest("Proxy did not receive app4 host address")

	def test_apps_receive_app4_host(self):
		self.assertTrue(self.env.get('APP4_HOST') is not None)
		self.assertTrue(self.env.get('APP4_HOSTS') is not None)

	def test_responds_to_hello(self):
		self.skipIfNoHost()
		headers = { 'Accept': 'application/json' }
		response = requests.get(self.url + '/hello', headers=headers)
		response.raise_for_status()

	@unittest.expectedFailure
	def test_receives_custom_properties(self):
		self.skipIfNoHost()
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

if __name__ == '__main__':
	unittest.main()
