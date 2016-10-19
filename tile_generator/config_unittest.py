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

	def test_requires_product_name(self):
		with self.assertRaises(SystemExit):
			Config().validate()

	def test_accepts_valid_product_name(self):
		Config(name='validname').validate()

	def test_accepts_valid_product_name_with_hyphen(self):
		Config(name='valid-name').validate()

	def test_accepts_valid_product_name_with_hyphens(self):
		Config(name='valid-name-too').validate()

	def test_accepts_valid_product_name_with_number(self):
		Config(name='valid-name-2').validate()

	def test_accepts_valid_product_name_with_one_letter_prefix(self):
		Config(name='p-tile').validate()

	def test_refuses_spaces_in_product_name(self):
		with self.assertRaises(SystemExit):
			Config(name='an invalid name').validate()

	def test_refuses_capital_letters_in_product_name(self):
		with self.assertRaises(SystemExit):
			Config(name='Invalid').validate()

	def test_refuses_underscores_in_product_name(self):
		with self.assertRaises(SystemExit):
			Config(name='invalid_name').validate()

	def test_refuses_product_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			Config(name='1-invalid-name').validate()

	def test_requires_package_names(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(name='validname', packages=[{'name': 'validname', 'type': 'app'}, {'type': 'app'}]).validate()
		self.assertIn('package is missing mandatory property \'name\'', err.getvalue())

	def test_requires_package_types(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(name='validname', packages=[{'name': 'validname', 'type': 'app'}, {'name': 'name'}]).validate()
		self.assertIn('package name is missing mandatory property \'type\'', err.getvalue())

	def test_refuses_invalid_type(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				Config(name='validname', packages=[{'name': 'validname', 'type': 'nonsense'}]).validate()
		self.assertIn('package validname has invalid type nonsense', err.getvalue())

	def test_accepts_valid_package_name(self):
		Config(name='validname', packages=[{'name': 'validname', 'type': 'app'}]).validate()

	def test_accepts_valid_package_name_with_hyphen(self):
		Config(name='validname', packages=[{'name': 'valid-name', 'type': 'app'}]).validate()

	def test_accepts_valid_package_name_with_hyphens(self):
		Config(name='validname', packages=[{'name': 'valid-name-too', 'type': 'app'}]).validate()

	def test_accepts_valid_package_name_with_number(self):
		Config(name='validname', packages=[{'name': 'valid-name-2', 'type': 'app'}]).validate()

	def test_refuses_spaces_in_package_name(self):
		with self.assertRaises(SystemExit):
			Config(name='validname', packages=[{'name': 'invalid name', 'type': 'app'}]).validate()

	def test_refuses_capital_letters_in_package_name(self):
		with self.assertRaises(SystemExit):
			Config(name='validname', packages=[{'name': 'Invalid', 'type': 'app'}]).validate()

	def test_refuses_underscores_in_package_name(self):
		with self.assertRaises(SystemExit):
			Config(name='validname', packages=[{'name': 'invalid_name', 'type': 'app'}]).validate()

	def test_refuses_package_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			Config(name='validname', packages=[{'name': '1-invalid-name', 'type': 'app'}]).validate()

class TestMemoryCalculation(unittest.TestCase):

	def setUp(self):
		self.release = {
			'total_memory': 0,
			'max_memory': 0
		}

	def test_correctly_handles_default(self):
		Config().update_memory(self.release, {})
		self.assertEqual(self.release['total_memory'], 1024)
		self.assertEqual(self.release['max_memory'], 1024)

	def test_correctly_interprets_m(self):
		Config().update_memory(self.release, { 'memory': '50m' })
		self.assertEqual(self.release['total_memory'], 50)
		self.assertEqual(self.release['max_memory'], 50)

	def test_correctly_interprets_M(self):
		Config().update_memory(self.release, { 'memory': '60M' })
		self.assertEqual(self.release['total_memory'], 60)
		self.assertEqual(self.release['max_memory'], 60)

	def test_correctly_interprets_mb(self):
		Config().update_memory(self.release, { 'memory': '70mb' })
		self.assertEqual(self.release['total_memory'], 70)
		self.assertEqual(self.release['max_memory'], 70)

	def test_correctly_interprets_MB(self):
		Config().update_memory(self.release, { 'memory': '80MB' })
		self.assertEqual(self.release['total_memory'], 80)
		self.assertEqual(self.release['max_memory'], 80)

	def test_correctly_interprets_g(self):
		Config().update_memory(self.release, { 'memory': '5g' })
		self.assertEqual(self.release['total_memory'], 5120)
		self.assertEqual(self.release['max_memory'], 5120)

	def test_correctly_interprets_G(self):
		Config().update_memory(self.release, { 'memory': '6G' })
		self.assertEqual(self.release['total_memory'], 6144)
		self.assertEqual(self.release['max_memory'], 6144)

	def test_correctly_interprets_gb(self):
		Config().update_memory(self.release, { 'memory': '7gb' })
		self.assertEqual(self.release['total_memory'], 7168)
		self.assertEqual(self.release['max_memory'], 7168)

	def test_correctly_interprets_GB(self):
		Config().update_memory(self.release, { 'memory': '8GB' })
		self.assertEqual(self.release['total_memory'], 8192)
		self.assertEqual(self.release['max_memory'], 8192)

	def test_correctly_ignores_whitespace(self):
		Config().update_memory(self.release, { 'memory': '9 GB' })
		self.assertEqual(self.release['total_memory'], 9216)
		self.assertEqual(self.release['max_memory'], 9216)

	def test_correctly_computes_total(self):
		self.release['total_memory'] = 1024
		Config().update_memory(self.release, { 'memory': '1GB' })
		self.assertEqual(self.release['total_memory'], 2048)

	def test_adjusts_max_if_bigger(self):
		self.release['max_memory'] = 512
		Config().update_memory(self.release, { 'memory': '1GB' })
		self.assertEqual(self.release['max_memory'], 1024)

	def test_leaves_max_if_smaller(self):
		self.release['max_memory'] = 2048
		Config().update_memory(self.release, { 'memory': '1GB' })
		self.assertEqual(self.release['max_memory'], 2048)

	def test_fails_without_unit(self):
		with self.assertRaises(SystemExit):
			Config().update_memory(self.release, { 'memory': '1024' })

	def test_fails_with_invalid_unit(self):
		with self.assertRaises(SystemExit):
			Config().update_memory(self.release, { 'memory': '1024xb' })

	def test_defaults_to_twice_total_size(self):
		config = Config()
		self.release['total_memory'] = 2048
		config.validate_memory_quota(self.release)
		self.assertEqual(config['org_quota'], 4096)

	def test_accepts_minimum_quota(self):
		config = Config(org_quota = 3072)
		release = dict(total_memory = 2048, max_memory = 1024)
		config.validate_memory_quota(release)
		self.assertEqual(config['org_quota'], 3072)

	def test_rejects_insufficient_quota(self):
		config = Config(org_quota = 3071)
		release = dict(total_memory = 2048, max_memory = 1024)
		with self.assertRaises(SystemExit):
			config.validate_memory_quota(release)

class TestDefaultOptions(unittest.TestCase):
	def test_purge_service_broker_is_true_by_default(self):
		config = Config({'name': 'tile-generator-unittest'})
		config.add_defaults()
		self.assertTrue(config['purge_service_brokers'])

	def test_purge_service_broker_is_overridden(self):
		config = Config({'purge_service_brokers': False,
				 'name': 'tile-generator-unittest'})
		config.add_defaults()
		self.assertFalse(config['purge_service_brokers'])

@mock.patch('os.path.getsize')
class TestVMDiskSize(unittest.TestCase):
	def test_min_vm_disk_size(self, mock_getsize):
		mock_getsize.return_value = 0
		config = Config({'name': 'tile-generator-unittest'})
		manifest = {'path': 'foo'}
		config.add_defaults()
		expected_size = config['compilation_vm_disk_size']
		config.update_compilation_vm_disk_size(manifest)
		self.assertEqual(config['compilation_vm_disk_size'], expected_size)

	def test_big_default_vm_disk_size(self, mock_getsize):
		config = Config({'name': 'tile-generator-unittest'})
		manifest = {'path': 'foo'}
		config.add_defaults()
		package_size = config['compilation_vm_disk_size']
		mock_getsize.return_value = package_size * 1024 * 1024 # megabytes to bytes.
		expected_size = 4 * package_size
		config.update_compilation_vm_disk_size(manifest)
		self.assertEqual(config['compilation_vm_disk_size'], expected_size)

if __name__ == '__main__':
	unittest.main()
