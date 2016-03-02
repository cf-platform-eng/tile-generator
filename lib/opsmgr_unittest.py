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