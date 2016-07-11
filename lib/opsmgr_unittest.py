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
import opsmgr
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

class TestInstallTriangulation(unittest.TestCase):

	def no_install_exists(self, id):
		return False

	def first_install_exists(self, id):
		return id == 1

	def twenty_installs_exist(self, id):
		return id > 0 and id <= 20

	def only_higher_installs_exist(self, id):
		return id > 10 and id <= 20

	def test_correctly_handles_no_installs(self):
		self.assertEquals(opsmgr.last_install(check=self.no_install_exists), 0)

	def test_correctly_handles_first_install(self):
		self.assertEquals(opsmgr.last_install(check=self.first_install_exists), 1)

	def test_correctly_handles_twenty_installs(self):
		self.assertEquals(opsmgr.last_install(check=self.twenty_installs_exist), 20)

#	def test_correctly_handles_only_higher_installs(self):
#		self.assertEquals(opsmgr.last_install(check=self.only_higher_installs_exist), 20)

if __name__ == '__main__':
	unittest.main()