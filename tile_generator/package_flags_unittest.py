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

import os
import unittest
import sys
import tempfile
import shutil

from contextlib import contextmanager
from StringIO import StringIO

from .package_flags import get_disk_size_for_chart


@contextmanager
def capture_output():
	new_out, new_err = StringIO(), StringIO()
	old_out, old_err = sys.stdout, sys.stderr
	try:
		sys.stdout, sys.stderr = new_out, new_err
		yield sys.stdout, sys.stderr
	finally:
		sys.stdout, sys.stderr = old_out, old_err


class TestGetDiskSpaceForChart(unittest.TestCase):
    chart_directory = None

    def setUp(self):
        self.chart_directory = tempfile.mkdtemp()

    def tearDown(self):
        if self.chart_directory != None:
            shutil.rmtree(self.chart_directory)

    def test_missing_directory_is_empty(self):
        size = get_disk_size_for_chart("/does/not/exist")
        self.assertEqual(size, 4096)

    def test_empty_directory_is_empty(self):
        size = get_disk_size_for_chart(self.chart_directory)
        self.assertEqual(size, 4096)

    def test_directory_with_file_shows_size(self):
        f = open(os.path.join(self.chart_directory, "a_file"), "w+")
        f.write("*" * (1024 * 1024))
        f.close()

        size = get_disk_size_for_chart(self.chart_directory)
        self.assertEqual(size, 4097)

    def test_directory_with_empty_subdirs(self):
        os.mkdir(os.path.join(self.chart_directory, "directory1"))
        os.mkdir(os.path.join(self.chart_directory, "directory2"))

        size = get_disk_size_for_chart(self.chart_directory)
        self.assertEqual(size, 4096)

    def test_directory_with_subdirs_with_files_shows_size(self):
        os.mkdir(os.path.join(self.chart_directory, "directory1"))
        f = open(os.path.join(self.chart_directory, "directory1", "file1"), "w+")
        f.write("*" * (1024 * 1024))
        f.close()
        os.mkdir(os.path.join(self.chart_directory, "directory2"))
        f = open(os.path.join(self.chart_directory, "directory2", "file2"), "w+")
        f.write("*" * (1024 * 1024))
        f.close()

        size = get_disk_size_for_chart(self.chart_directory)
        self.assertEqual(size, 4098)

if __name__ == '__main__':
	unittest.main()
