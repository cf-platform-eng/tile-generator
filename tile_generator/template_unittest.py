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
from . import template

class TestPropertyFilter(unittest.TestCase):
	def test_property_filter_simple_property(self):
		property = {
			'name': 'prop',
			'type': 'string',
		}
		result = template.render_property(property)
		self.assertEqual(result, {'prop': '(( .properties.prop.value ))' })

	def test_property_filter_complex_property(self):
		property = {
			'name': 'prop',
			'type': 'simple_credentials',
		}
		result = template.render_property(property)
		self.assertEqual(result, {
			'prop': {
				'identity': '(( .properties.prop.identity ))',
				'password': '(( .properties.prop.password ))',
			}
		})

class TestVariableNameFilter(unittest.TestCase):
	def test_no_change(self):
		self.assertEqual(template.render_shell_variable_name('FOO'), 'FOO')
		self.assertEqual(template.render_shell_variable_name('F00'), 'F00')
		self.assertEqual(template.render_shell_variable_name('FOO_BAR'), 'FOO_BAR')

	def test_hyphen_to_underscore(self):
		self.assertEqual(template.render_shell_variable_name('FOO-BAR'), 'FOO_BAR')
		self.assertEqual(template.render_shell_variable_name('FOO--BAR'), 'FOO_BAR')

	def test_uppercases_letters(self):
		self.assertEqual(template.render_shell_variable_name('foo'), 'FOO')
		self.assertEqual(template.render_shell_variable_name('Foo'), 'FOO')
