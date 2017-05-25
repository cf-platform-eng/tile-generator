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
from . import config
from .config import Config
import sys
import tempfile
from contextlib import contextmanager
from StringIO import StringIO
import mock

@contextmanager
def capture_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err

class TestVersionMethods(unittest.TestCase):

	def test_accepts_valid_semver(self):
		self.assertTrue(config.is_semver('11.2.25'))

	def test_accepts_valid_semver_with_prerelease(self):
		self.assertTrue(config.is_semver('11.2.25-alpha.1'))

	def test_accepts_valid_semver_with_config(self):
		self.assertTrue(config.is_semver('11.2.25+gb.23'))

	def test_accepts_valid_semver_with_prerelease_and_config(self):
		self.assertTrue(config.is_semver('11.2.25-alpha.1+gb.23'))

	def test_rejects_short_semver(self):
		self.assertFalse(config.is_semver('11.2'))

	def test_rejects_long_semver(self):
		self.assertFalse(config.is_semver('11.2.25.3'))

	def test_rejects_non_numeric_semver(self):
		self.assertFalse(config.is_semver('11.2.25dev1'))

	def test_initial_version(self):
		config = Config(history={})
		config.set_version(None)
		self.assertEquals(config['version'], '0.0.1')

	def test_default_version_update(self):
		config = Config(history={'version':'1.2.3'})
		config.set_version(None)
		self.assertEquals(config['version'], '1.2.4')

	def test_patch_version_update(self):
		config = Config(history={'version':'1.2.3'})
		config.set_version('patch')
		self.assertEquals(config['version'], '1.2.4')

	def test_minor_version_update(self):
		config = Config(history={'version':'1.2.3'})
		config.set_version('minor')
		self.assertEquals(config['version'], '1.3.0')

	def test_major_version_update(self):
		config = Config(history={'version':'1.2.3'})
		config.set_version('major')
		self.assertEquals(config['version'], '2.0.0')

	def test_explicit_version_update(self):
		config = Config(history={'version':'1.2.3'})
		config.set_version('5.0.1')
		self.assertEquals(config['version'], '5.0.1')

	def test_annotated_version_update(self):
		config = Config(history={'version':'1.2.3-alpha.1'})
		config.set_version('1.2.4')
		self.assertEquals(config['version'], '1.2.4')

	def test_illegal_old_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(history={'version':'nonsense'}).set_version('patch')
		self.assertIn('prior version must be in semver format', err.getvalue())

	def test_illegal_new_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(history={'version':'1.2.3'}).set_version('nonsense')
		self.assertIn('Argument must specify', err.getvalue())

	def test_illegal_annotated_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(history={'version':'1.2.3-alpha.1'}).set_version(None)
		self.assertIn('The prior version was 1.2.3-alpha.1', err.getvalue())
		self.assertIn('and must not include a label', err.getvalue())

	def test_saves_initial_version(self):
		history = {}
		Config(history=history).set_version('0.0.1')
		self.assertEquals(history.get('version'), '0.0.1')
		self.assertEquals(len(history.get('history', [])), 0)

	def test_saves_initial_history(self):
		history = { 'version': '0.0.1' }
		Config(history=history).set_version('0.0.2')
		self.assertEquals(history.get('version'), '0.0.2')
		self.assertEquals(len(history.get('history')), 1)
		self.assertEquals(history.get('history')[0], '0.0.1')

	def test_saves_additional_history(self):
		history = { 'version': '0.0.2', 'history': [ '0.0.1' ] }
		Config(history=history).set_version('0.0.3')
		self.assertEquals(history.get('version'), '0.0.3')
		self.assertEquals(len(history.get('history')), 2)
		self.assertEquals(history.get('history')[0], '0.0.1')
		self.assertEquals(history.get('history')[1], '0.0.2')

class TestConfigValidation(unittest.TestCase):

	def setUp(self):
		self.icon_file = tempfile.NamedTemporaryFile()
		self.config = Config(name='validname', icon_file=self.icon_file.name)

	def tearDown(self):
		self.icon_file.close()

	def test_accepts_minimal_config(self):
		self.config.validate()

	def test_requires_product_name(self):
		with self.assertRaises(SystemExit):
			del self.config['name']
			self.config.validate()

	def test_accepts_valid_product_name_with_hyphen(self):
		self.config['name'] = 'valid-name'
		self.config.validate()

	def test_accepts_valid_product_name_with_hyphens(self):
		self.config['name'] = 'valid-name-too'
		self.config.validate()

	def test_accepts_valid_product_name_with_number(self):
		self.config['name'] = 'valid-name-2'
		self.config.validate()

	def test_accepts_valid_product_name_with_one_letter_prefix(self):
		self.config['name'] = 'p-tile'
		self.config.validate()

	def test_refuses_spaces_in_product_name(self):
		with self.assertRaises(SystemExit):
			self.config['name'] = 'an invalid name'
			self.config.validate()

	def test_refuses_capital_letters_in_product_name(self):
		with self.assertRaises(SystemExit):
			self.config['name'] = 'Invalid'
			self.config.validate()

	def test_refuses_underscores_in_product_name(self):
		with self.assertRaises(SystemExit):
			self.config['name'] = 'invalid_name'
			self.config.validate()

	def test_refuses_product_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			self.config['name'] = '1-invalid-name'
			self.config.validate()

	def test_requires_package_names(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}, {'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
				self.config.validate()
		self.assertIn('package is missing mandatory property \'name\'', err.getvalue())

	def test_requires_package_types(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}, {'name': 'name'}]
				self.config.validate()
		self.assertIn('package name is missing mandatory property \'type\'', err.getvalue())

	def test_refuses_invalid_type(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				self.config['packages'] = [{'name': 'validname', 'type': 'nonsense'}]
				self.config.validate()
		self.assertIn('package validname has invalid type nonsense', err.getvalue())

	def test_accepts_valid_package_name(self):
		self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
		self.config.validate()

	def test_accepts_valid_package_name_with_hyphen(self):
		self.config['packages'] = [{'name': 'valid-name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
		self.config.validate()

	def test_accepts_valid_package_name_with_hyphens(self):
		self.config['packages'] = [{'name': 'valid-name-too', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
		self.config.validate()

	def test_accepts_valid_package_name_with_number(self):
		self.config['packages'] = [{'name': 'valid-name-2', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
		self.config.validate()

	def test_refuses_spaces_in_package_name(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'invalid name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
			self.config.validate()

	def test_refuses_capital_letters_in_package_name(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'Invalid', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
			self.config.validate()

	def test_refuses_underscores_in_package_name(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'invalid_name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
			self.config.validate()

	def test_refuses_package_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': '1-invalid-name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
			self.config.validate()

	def test_refuses_docker_bosh_package_without_image(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'bad-docker-bosh', 'type': 'docker-bosh'}]
			self.config.validate()

	def test_accepts_docker_bosh_package_with_image(self):
		self.config['packages'] = [{'name': 'bad-docker-bosh', 'type': 'docker-bosh', 'docker_images': ['my/image']}]
		self.config.validate()

	def test_requires_icon_file(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out, err):
				del self.config['icon_file']
				self.config.validate()
		self.assertIn('icon_file', err.getvalue())

	def test_refuses_empty_icon_file(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out, err):
				self.config['icon_file'] = None
				self.config.validate()
		self.assertIn('icon_file', err.getvalue())

	def test_refuses_invalid_icon_file(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out, err):
				self.config['icon_file'] = '/this/file/does/not/exist'
				self.config.validate()
		self.assertIn('icon_file', err.getvalue())

	def test_requires_buildpack_for_app_broker(self):
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'packagename', 'type': 'app'}]
			self.config.validate()
		with self.assertRaises(SystemExit):
			self.config['packages'] = [{'name': 'packagename', 'type': 'app-broker'}]
			self.config.validate()

	def test_buildpack_not_required_for_docker_app(self):
		self.config['packages'] = [{'name': 'packagename', 'type': 'docker-app'}]
		self.config.validate()

class TestDefaultOptions(unittest.TestCase):
	def test_purge_service_broker_is_true_by_default(self):
		config = Config({'name': 'tile-generator-unittest'})
		with mock.patch('tile_generator.config.Config.latest_stemcell', return_value='1234'):
			config.add_defaults()
		self.assertTrue(config['purge_service_brokers'])

	def test_purge_service_broker_is_overridden(self):
		config = Config({'purge_service_brokers': False,
				 'name': 'tile-generator-unittest'})
		with mock.patch('tile_generator.config.Config.latest_stemcell', return_value='1234'):
			config.add_defaults()
		self.assertFalse(config['purge_service_brokers'])

	def test_normalize_jobs_default_job_properties(self):
		config = Config({
			'releases': [{
				'jobs': [{
					'name': 'my-job'
				}]
			}]
		})
		config.normalize_jobs()
		self.assertEqual(config['releases'][0]['jobs'][0]['properties'], {})

@mock.patch('os.path.getsize')
class TestVMDiskSize(unittest.TestCase):
	def test_min_vm_disk_size(self, mock_getsize):
		mock_getsize.return_value = 0
		config = Config({'name': 'tile-generator-unittest'})
		manifest = {'path': 'foo'}
		with mock.patch('tile_generator.config.Config.latest_stemcell', return_value='1234'):
			config.add_defaults()
		expected_size = config['compilation_vm_disk_size']
		with mock.patch('os.path.exists',return_value = True):
			config.update_compilation_vm_disk_size(manifest)
		self.assertEqual(config['compilation_vm_disk_size'], expected_size)

	def test_big_default_vm_disk_size(self, mock_getsize):
		config = Config({'name': 'tile-generator-unittest'})
		manifest = {'path': 'foo'}
		with mock.patch('tile_generator.config.Config.latest_stemcell', return_value='1234'):
			config.add_defaults()
		package_size = config['compilation_vm_disk_size']
		mock_getsize.return_value = package_size * 1024 * 1024 # megabytes to bytes.
		expected_size = 4 * package_size
		with mock.patch('os.path.exists', return_value=True):
			config.update_compilation_vm_disk_size(manifest)
		self.assertEqual(config['compilation_vm_disk_size'], expected_size)

if __name__ == '__main__':
	unittest.main()
