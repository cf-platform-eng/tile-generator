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
import build
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

class TestMemoryCalculation(unittest.TestCase):

	def setUp(self):
		self.context = {
			'total_memory': 0,
			'max_memory': 0
		}

	def test_correctly_handles_default(self):
		build.update_memory(self.context, {})
		self.assertEquals(self.context['total_memory'], 1024)
		self.assertEquals(self.context['max_memory'], 1024)

	def test_correctly_interprets_m(self):
		build.update_memory(self.context, { 'memory': '50m' })
		self.assertEquals(self.context['total_memory'], 50)
		self.assertEquals(self.context['max_memory'], 50)

	def test_correctly_interprets_M(self):
		build.update_memory(self.context, { 'memory': '60M' })
		self.assertEquals(self.context['total_memory'], 60)
		self.assertEquals(self.context['max_memory'], 60)

	def test_correctly_interprets_mb(self):
		build.update_memory(self.context, { 'memory': '70mb' })
		self.assertEquals(self.context['total_memory'], 70)
		self.assertEquals(self.context['max_memory'], 70)

	def test_correctly_interprets_MB(self):
		build.update_memory(self.context, { 'memory': '80MB' })
		self.assertEquals(self.context['total_memory'], 80)
		self.assertEquals(self.context['max_memory'], 80)

	def test_correctly_interprets_g(self):
		build.update_memory(self.context, { 'memory': '5g' })
		self.assertEquals(self.context['total_memory'], 5120)
		self.assertEquals(self.context['max_memory'], 5120)

	def test_correctly_interprets_G(self):
		build.update_memory(self.context, { 'memory': '6G' })
		self.assertEquals(self.context['total_memory'], 6144)
		self.assertEquals(self.context['max_memory'], 6144)

	def test_correctly_interprets_gb(self):
		build.update_memory(self.context, { 'memory': '7gb' })
		self.assertEquals(self.context['total_memory'], 7168)
		self.assertEquals(self.context['max_memory'], 7168)

	def test_correctly_interprets_GB(self):
		build.update_memory(self.context, { 'memory': '8GB' })
		self.assertEquals(self.context['total_memory'], 8192)
		self.assertEquals(self.context['max_memory'], 8192)

	def test_correctly_ignores_whitespace(self):
		build.update_memory(self.context, { 'memory': '9 GB' })
		self.assertEquals(self.context['total_memory'], 9216)
		self.assertEquals(self.context['max_memory'], 9216)

	def test_correctly_computes_total(self):
		self.context['total_memory'] = 1024
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEquals(self.context['total_memory'], 2048)

	def test_adjusts_max_if_bigger(self):
		self.context['max_memory'] = 512
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEquals(self.context['max_memory'], 1024)

	def test_leaves_max_if_smaller(self):
		self.context['max_memory'] = 2048
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEquals(self.context['max_memory'], 2048)

	def test_fails_without_unit(self):
		with self.assertRaises(SystemExit):
			build.update_memory(self.context, { 'memory': '1024' })

	def test_fails_with_invalid_unit(self):
		with self.assertRaises(SystemExit):
			build.update_memory(self.context, { 'memory': '1024xb' })

	def test_defaults_to_twice_total_size(self):
		self.context['total_memory'] = 2048
		build.validate_memory_quota(self.context)
		self.assertEquals(self.context['org_quota'], 4096)

	def test_accepts_minimum_quota(self):
		self.context['total_memory'] = 2048
		self.context['max_memory'] = 1024
		self.context['org_quota'] = 3072
		build.validate_memory_quota(self.context)
		self.assertEquals(self.context['org_quota'], 3072)

	def test_rejects_insufficient_quota(self):
		self.context['total_memory'] = 2048
		self.context['max_memory'] = 1024
		self.context['org_quota'] = 3071
		with self.assertRaises(SystemExit):
			build.validate_memory_quota(self.context)

class TestConfigValidation(unittest.TestCase):

	def test_requires_product_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({})

	def test_accepts_valid_product_name(self):
		build.validate_config({'name': 'validname'})

	def test_accepts_valid_product_name_with_hyphen(self):
		build.validate_config({'name': 'valid-name'})

	def test_accepts_valid_product_name_with_hyphens(self):
		build.validate_config({'name': 'valid-name-too'})

	def test_accepts_valid_product_name_with_number(self):
		build.validate_config({'name': 'valid-name-2'})

	def test_refuses_spaces_in_product_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'an invalid name'})

	def test_refuses_capital_letters_in_product_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'Invalid'})

	def test_refuses_underscores_in_product_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'invalid_name'})

	def test_refuses_product_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': '1-invalid-name'})

	def test_requires_package_names(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'validname', 'packages': [{'name': 'validname'}, {}]})

	def test_accepts_valid_package_name(self):
		build.validate_config({'name': 'validname', 'packages': [{'name': 'validname'}]})

	def test_accepts_valid_package_name_with_hyphen(self):
		build.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name'}]})

	def test_accepts_valid_package_name_with_hyphens(self):
		build.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name-too'}]})

	def test_accepts_valid_package_name_with_number(self):
		build.validate_config({'name': 'validname', 'packages': [{'name': 'valid-name-2'}]})

	def test_refuses_spaces_in_package_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'validname', 'packages': [{'name': 'invalid name'}]})

	def test_refuses_capital_letters_in_package_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'validname', 'packages': [{'name': 'Invalid'}]})

	def test_refuses_underscores_in_package_name(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'validname', 'packages': [{'name': 'invalid_name'}]})

	def test_refuses_package_name_starting_with_number(self):
		with self.assertRaises(SystemExit):
			build.validate_config({'name': 'validname', 'packages': [{'name': '1-invalid-name'}]})

class TestVersionMethods(unittest.TestCase):

	def test_accepts_valid_semver(self):
		self.assertTrue(build.is_semver('11.2.25'))

	def test_accepts_valid_semver_with_prerelease(self):
		self.assertTrue(build.is_semver('11.2.25-alpha.1'))

	def test_accepts_valid_semver_with_build(self):
		self.assertTrue(build.is_semver('11.2.25+gb.23'))

	def test_accepts_valid_semver_with_prerelease_and_build(self):
		self.assertTrue(build.is_semver('11.2.25-alpha.1+gb.23'))

	def test_rejects_short_semver(self):
		self.assertFalse(build.is_semver('11.2'))

	def test_rejects_long_semver(self):
		self.assertFalse(build.is_semver('11.2.25.3'))

	def test_rejects_non_numeric_semver(self):
		self.assertFalse(build.is_semver('11.2.25dev1'))

	def test_initial_version(self):
		self.assertEquals(build.update_version({}, None), '0.0.1')

	def test_default_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, None), '1.2.4')

	def test_patch_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'patch'), '1.2.4')

	def test_minor_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'minor'), '1.3.0')

	def test_major_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'major'), '2.0.0')

	def test_explicit_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, '5.0.1'), '5.0.1')

	def test_annotated_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3-alpha.1' }, '1.2.4'), '1.2.4')

	def test_illegal_old_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				build.update_version({ 'version': 'nonsense' }, 'patch')
		self.assertIn('prior version must be in semver format', err.getvalue())

	def test_illegal_new_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				build.update_version({ 'version': '1.2.3' }, 'nonsense')
		self.assertIn('Argument must specify', err.getvalue())

	def test_illegal_annotated_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				build.update_version({ 'version': '1.2.3-alpha.1' }, None)
		self.assertIn('The prior version was 1.2.3-alpha.1', err.getvalue())
		self.assertIn('and must not include a label', err.getvalue())

	def test_saves_initial_version(self):
		history = {}
		build.update_version(history, '0.0.1')
		self.assertEquals(history.get('version'), '0.0.1')
		self.assertEquals(len(history.get('history', [])), 0)

	def test_saves_initial_history(self):
		history = { 'version': '0.0.1' }
		build.update_version(history, '0.0.2')
		self.assertEquals(history.get('version'), '0.0.2')
		self.assertEquals(len(history.get('history')), 1)
		self.assertEquals(history.get('history')[0], '0.0.1')

	def test_saves_additional_history(self):
		history = { 'version': '0.0.2', 'history': [ '0.0.1' ] }
		build.update_version(history, '0.0.3')
		self.assertEquals(history.get('version'), '0.0.3')
		self.assertEquals(len(history.get('history')), 2)
		self.assertEquals(history.get('history')[0], '0.0.1')
		self.assertEquals(history.get('history')[1], '0.0.2')

if __name__ == '__main__':
	unittest.main()
