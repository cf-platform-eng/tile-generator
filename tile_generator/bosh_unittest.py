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

import sys
import tarfile
import tempfile
import yaml
from contextlib import contextmanager
from io import StringIO

import unittest
from . import bosh
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


class TestBoshCheck(unittest.TestCase):
	@mock.patch('distutils.spawn.find_executable')
	@mock.patch('subprocess.check_output')
	@mock.patch('sys.exit')
	def test_passes_when_on_path(self, mock_sys_exit, mock_output, mock_find_executable):
		mock_find_executable.return_value = 'Some'
		mock_output.return_value = 'version 2.'

		bosh.ensure_bosh()


		mock_sys_exit.assert_not_called()


	@mock.patch('distutils.spawn.find_executable')
	@mock.patch('sys.exit')
	def test_exits_when_not_present(self, mock_sys_exit, mock_find_executable):
		mock_find_executable.return_value = None

		bosh.ensure_bosh()

		mock_sys_exit.assert_called()

class TestManifest(unittest.TestCase):
	def test_get_manifest_finds_bare_release_mf(self):
		with tempfile.NamedTemporaryFile() as tf:
			tar = tarfile.open(tf.name, mode='w')
			manifest_text = 'manifest'
			manifest_yaml = yaml.safe_dump(manifest_text)
			info = tarfile.TarInfo('release.MF')
			info.size = len(manifest_yaml)
			tar.addfile(tarinfo=info, fileobj=StringIO(unicode(manifest_yaml)))
			tar.close()
			br = bosh.BoshRelease({'name': 'my-release'}, None)
			actual = br.get_manifest(tf.name)
			self.assertEqual(actual, manifest_text)

	def test_get_manifest_finds_dot_slash_release_mf(self):
		with tempfile.NamedTemporaryFile() as tf:
			tar = tarfile.open(tf.name, mode='w')
			manifest_text = 'manifest'
			manifest_yaml = yaml.safe_dump(manifest_text)
			info = tarfile.TarInfo('./release.MF')
			info.size = len(manifest_yaml)
			tar.addfile(tarinfo=info, fileobj=StringIO(unicode(manifest_yaml)))
			tar.close()
			br = bosh.BoshRelease({'name': 'my-release'}, None)
			actual = br.get_manifest(tf.name)
			self.assertEqual(actual, manifest_text)

	def test_get_manifest_throws_when_no_manifest(self):
		with tempfile.NamedTemporaryFile() as tf:
			tar = tarfile.open(tf.name, mode='w')
			tar.close()
			br = bosh.BoshRelease({'name': 'my-release'}, None)
			with self.assertRaises(Exception):
				actual = br.get_manifest(tf.name)

if __name__ == '__main__':
	unittest.main()
