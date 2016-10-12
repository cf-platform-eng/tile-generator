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
from click.testing import CliRunner
import os
import shutil
import tempfile
from . import tile

class TestTileInit(unittest.TestCase):
	def test_tile_init_works(self):
		tmpdir = tempfile.mkdtemp()
		try:
			tiledir = os.path.join(tmpdir, 'my-tile')
			runner = CliRunner()
			result = runner.invoke(tile.init_cmd, [tiledir])
			self.assertEqual(result.exit_code, 0)
			self.assertTrue(os.path.isfile(os.path.join(tiledir, 'tile.yml')))
		finally:
			shutil.rmtree(tmpdir)
