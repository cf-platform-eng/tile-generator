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

	def test_has_valid_migrations(self):
		self.assertTrue(os.path.exists('product/migrations/v1'))
		files = glob.glob('product/migrations/v1/*.js')
		self.assertEqual(len(files), 1)

	def test_has_valid_metadata(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0]) # Ensure corrent yaml syntax

	def test_contains_tile_yml(self):
		self.assertTrue(os.path.exists('product/tile-generator'))
		files = glob.glob('product/tile-generator/tile.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0])

class VerifyProperties(unittest.TestCase):

	def setUp(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		self.metadata = read_yaml(files[0])

	def test_optional(self):
		blueprints = self.metadata['property_blueprints']
		self.assertFalse(find_by_name(blueprints, 'author')['optional'])
		self.assertTrue(find_by_name(blueprints, 'customer_name')['optional'])
		self.assertFalse(find_by_name(blueprints, 'street_address')['optional'])

	def test_bosh_release_has_properties(self):
		job = find_by_name(self.metadata['job_types'], 'redis_leader_z1')
		self.assertIn('author', job['manifest'])

	def test_default_internet_connected(self):
		job = find_by_name(self.metadata['job_types'], 'redis_leader_z1')
		self.assertIn('default_internet_connected', job)
		self.assertFalse(job['default_internet_connected'])

	def test_run_errand_default(self):
		errand = find_by_name(self.metadata['post_deploy_errands'], 'acceptance-tests')
		self.assertEqual(errand['run_post_deploy_errand_default'], 'when-changed')

	def test_bosh_release_properties_merged(self):
		job = find_by_name(self.metadata['job_types'], 'acceptance-tests')
		manifest = yaml.safe_load(job['manifest'])
		cf = manifest['cf']
		self.assertIn('some', cf) # Property defined in tile.yml.
		self.assertIn('admin_user', cf) # Auto-included property.

	def test_deploy_all_has_broker_user_and_password(self):
		job = find_by_name(self.metadata['job_types'], 'deploy-all')
		manifest = yaml.safe_load(job['manifest'])
		broker = manifest['tg_test_broker1']
		self.assertIn('user', broker)
		self.assertIn('password', broker)

class VerifyConstraints(unittest.TestCase):

	def setUp(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		self.metadata = read_yaml(files[0])

	def test_resource_constraints(self):
		job = find_by_name(self.metadata['job_types'], 'acceptance-tests')
		resource_defs = job['resource_definitions']
		self.assertEqual(find_by_name(resource_defs, 'cpu')['constraints']['min'], 2)
		self.assertEqual(find_by_name(resource_defs, 'ephemeral_disk')['constraints']['min'], 4096)
		self.assertEqual(find_by_name(resource_defs, 'persistent_disk')['constraints']['min'], 0)
		self.assertEqual(find_by_name(resource_defs, 'ram')['constraints']['min'], 512)

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
