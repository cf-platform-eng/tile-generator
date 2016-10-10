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

from __future__ import absolute_import, division, print_function
import unittest
from . import build
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
		self.assertEqual(self.context['total_memory'], 1024)
		self.assertEqual(self.context['max_memory'], 1024)

	def test_correctly_interprets_m(self):
		build.update_memory(self.context, { 'memory': '50m' })
		self.assertEqual(self.context['total_memory'], 50)
		self.assertEqual(self.context['max_memory'], 50)

	def test_correctly_interprets_M(self):
		build.update_memory(self.context, { 'memory': '60M' })
		self.assertEqual(self.context['total_memory'], 60)
		self.assertEqual(self.context['max_memory'], 60)

	def test_correctly_interprets_mb(self):
		build.update_memory(self.context, { 'memory': '70mb' })
		self.assertEqual(self.context['total_memory'], 70)
		self.assertEqual(self.context['max_memory'], 70)

	def test_correctly_interprets_MB(self):
		build.update_memory(self.context, { 'memory': '80MB' })
		self.assertEqual(self.context['total_memory'], 80)
		self.assertEqual(self.context['max_memory'], 80)

	def test_correctly_interprets_g(self):
		build.update_memory(self.context, { 'memory': '5g' })
		self.assertEqual(self.context['total_memory'], 5120)
		self.assertEqual(self.context['max_memory'], 5120)

	def test_correctly_interprets_G(self):
		build.update_memory(self.context, { 'memory': '6G' })
		self.assertEqual(self.context['total_memory'], 6144)
		self.assertEqual(self.context['max_memory'], 6144)

	def test_correctly_interprets_gb(self):
		build.update_memory(self.context, { 'memory': '7gb' })
		self.assertEqual(self.context['total_memory'], 7168)
		self.assertEqual(self.context['max_memory'], 7168)

	def test_correctly_interprets_GB(self):
		build.update_memory(self.context, { 'memory': '8GB' })
		self.assertEqual(self.context['total_memory'], 8192)
		self.assertEqual(self.context['max_memory'], 8192)

	def test_correctly_ignores_whitespace(self):
		build.update_memory(self.context, { 'memory': '9 GB' })
		self.assertEqual(self.context['total_memory'], 9216)
		self.assertEqual(self.context['max_memory'], 9216)

	def test_correctly_computes_total(self):
		self.context['total_memory'] = 1024
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEqual(self.context['total_memory'], 2048)

	def test_adjusts_max_if_bigger(self):
		self.context['max_memory'] = 512
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEqual(self.context['max_memory'], 1024)

	def test_leaves_max_if_smaller(self):
		self.context['max_memory'] = 2048
		build.update_memory(self.context, { 'memory': '1GB' })
		self.assertEqual(self.context['max_memory'], 2048)

	def test_fails_without_unit(self):
		with self.assertRaises(SystemExit):
			build.update_memory(self.context, { 'memory': '1024' })

	def test_fails_with_invalid_unit(self):
		with self.assertRaises(SystemExit):
			build.update_memory(self.context, { 'memory': '1024xb' })

	def test_defaults_to_twice_total_size(self):
		self.context['total_memory'] = 2048
		build.validate_memory_quota(self.context)
		self.assertEqual(self.context['org_quota'], 4096)

	def test_accepts_minimum_quota(self):
		self.context['total_memory'] = 2048
		self.context['max_memory'] = 1024
		self.context['org_quota'] = 3072
		build.validate_memory_quota(self.context)
		self.assertEqual(self.context['org_quota'], 3072)

	def test_rejects_insufficient_quota(self):
		self.context['total_memory'] = 2048
		self.context['max_memory'] = 1024
		self.context['org_quota'] = 3071
		with self.assertRaises(SystemExit):
			build.validate_memory_quota(self.context)

if __name__ == '__main__':
	unittest.main()
