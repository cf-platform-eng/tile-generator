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

def find_by_identifier(lst, id):
	for item in lst:
		if item['identifier'] == id:
			return item
	return None

class VerifyApp5(unittest.TestCase):

	def setUp(self):
		pass

	def test_resource_config(self):
		version = opsmgr.get_version()
		# Resource config only 1.8+
		if version[0] < 1 or version[1] < 8:
			return
		settings = opsmgr.get('/api/installation_settings').json()
		products = settings['products']
		product = find_by_identifier(products, 'test-tile')
		jobs = product['jobs']
		job = find_by_identifier(jobs, 'redis_z1')
		job_resource_config = opsmgr.get(
			'/api/v0/staged/products/{}/jobs/{}/resource_config'.format(
				product['guid'],
				job['guid'],
			)
		).json()
		self.assertTrue('persistent_disk' in job_resource_config)
		self.assertTrue('size_mb' in job_resource_config['persistent_disk'])
		self.assertEqual(job_resource_config['persistent_disk']['size_mb'], '10240')

if __name__ == '__main__':
	unittest.main()
