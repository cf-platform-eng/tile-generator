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
import sys
import os
import glob
import yaml

class VerifyTile(unittest.TestCase):

	def test_has_valid_content_migrations(self):
		self.assertTrue(os.path.exists('product/content_migrations'))
		files = glob.glob('product/content_migrations/*.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0]) # Ensure corrent yaml syntax

	def test_has_valid_metadata(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0]) # Ensure corrent yaml syntax

class VerifyProperties(unittest.TestCase):

	def setUp(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		self.config = read_yaml(files[0])

	def test_optional(self):
		blueprints = self.config['property_blueprints']
		self.assertFalse(find_by_name(blueprints, 'author')['optional'])
		self.assertTrue(find_by_name(blueprints, 'customer_name')['optional'])
		self.assertFalse(find_by_name(blueprints, 'street_address')['optional'])

	def test_bosh_release_has_properties(self):
		job = find_by_name(self.config['job_types'], 'redis_leader_z1')
		self.assertIn('author', job['manifest'])

	def test_default_internet_connected(self):
		job = find_by_name(self.config['job_types'], 'redis_leader_z1')
		self.assertIn('default_internet_connected', job)
		self.assertFalse(job['default_internet_connected'])

	def test_run_errand_default(self):
		errand = find_by_name(self.config['post_deploy_errands'], 'acceptance-tests')
		self.assertEqual(errand['run_post_deploy_errand_default'], 'when-changed')

def find_by_name(lst, name):
	return next(x for x in lst if x.get('name', None) == name)

def read_yaml(filename):
	with open(filename, 'rb') as file:
		return yaml.safe_load(file)

def read_file(filename):
	with open(filename, 'rb') as file:
		return file.read()

if __name__ == '__main__':
	unittest.main()
