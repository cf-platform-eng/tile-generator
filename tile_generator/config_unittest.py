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
		self.assertEquals(config.update_version({}, None), '0.0.1')

	def test_default_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3' }, None), '1.2.4')

	def test_patch_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3' }, 'patch'), '1.2.4')

	def test_minor_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3' }, 'minor'), '1.3.0')

	def test_major_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3' }, 'major'), '2.0.0')

	def test_explicit_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3' }, '5.0.1'), '5.0.1')

	def test_annotated_version_update(self):
		self.assertEquals(config.update_version({ 'version': '1.2.3-alpha.1' }, '1.2.4'), '1.2.4')

	def test_illegal_old_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				config.update_version({ 'version': 'nonsense' }, 'patch')
		self.assertIn('prior version must be in semver format', err.getvalue())

	def test_illegal_new_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				config.update_version({ 'version': '1.2.3' }, 'nonsense')
		self.assertIn('Argument must specify', err.getvalue())

	def test_illegal_annotated_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				config.update_version({ 'version': '1.2.3-alpha.1' }, None)
		self.assertIn('The prior version was 1.2.3-alpha.1', err.getvalue())
		self.assertIn('and must not include a label', err.getvalue())

	def test_saves_initial_version(self):
		history = {}
		config.update_version(history, '0.0.1')
		self.assertEquals(history.get('version'), '0.0.1')
		self.assertEquals(len(history.get('history', [])), 0)

	def test_saves_initial_history(self):
		history = { 'version': '0.0.1' }
		config.update_version(history, '0.0.2')
		self.assertEquals(history.get('version'), '0.0.2')
		self.assertEquals(len(history.get('history')), 1)
		self.assertEquals(history.get('history')[0], '0.0.1')

	def test_saves_additional_history(self):
		history = { 'version': '0.0.2', 'history': [ '0.0.1' ] }
		config.update_version(history, '0.0.3')
		self.assertEquals(history.get('version'), '0.0.3')
		self.assertEquals(len(history.get('history')), 2)
		self.assertEquals(history.get('history')[0], '0.0.1')
		self.assertEquals(history.get('history')[1], '0.0.2')

class TestConfigValidation(unittest.TestCase):

	def test_requires_product_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({})

	def test_accepts_valid_product_name(self):
		config.validate_config({'name': 'validname'})

	def test_accepts_valid_product_name_with_hyphen(self):
		config.validate_config({'name': 'valid-name'})

	def test_accepts_valid_product_name_with_hyphens(self):
		config.validate_config({'name': 'valid-name-too'})

	def test_accepts_valid_product_name_with_number(self):
		config.validate_config({'name': 'valid-name-2'})

	def test_refuses_spaces_in_product_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'an invalid name'})

	def test_refuses_capital_letters_in_product_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'Invalid'})

	def test_refuses_underscores_in_product_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'invalid_name'})

	def test_refuses_product_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': '1-invalid-name'})

	def test_requires_package_names(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'validname', 'packages': [{'name': 'validname'}, {}]})

	def test_accepts_valid_package_name(self):
		config.validate_config({'name': 'validname', 'packages': [{'name': 'validname'}]})

	def test_accepts_valid_package_name_with_hyphen(self):
		config.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name'}]})

	def test_accepts_valid_package_name_with_hyphens(self):
		config.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name-too'}]})

	def test_accepts_valid_package_name_with_number(self):
		config.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name-2'}]})

	def test_refuses_spaces_in_package_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'validname', 'packages': [{'name': 'invalid name'}]})

	def test_refuses_capital_letters_in_package_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'validname', 'packages': [{'name': 'Invalid'}]})

	def test_refuses_underscores_in_package_name(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'validname', 'packages': [{'name': 'invalid_name'}]})

	def test_refuses_package_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			config.validate_config({'name': 'validname', 'packages': [{'name': '1-invalid-name'}]})

if __name__ == '__main__':
	unittest.main()
