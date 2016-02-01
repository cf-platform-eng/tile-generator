import unittest
import build

class TestVersionMethods(unittest.TestCase):

	def test_accepts_valid_semver(self):
		self.assertTrue(build.is_semver('11.2.25'))

	def test_rejects_short_semver(self):
		self.assertFalse(build.is_semver('11.2'))

	def test_rejects_long_semver(self):
		self.assertFalse(build.is_semver('11.2.25.3'))

	def test_rejects_non_numeric_semver(self):
		self.assertFalse(build.is_semver('11.2.25dev1'))

if __name__ == '__main__':
	unittest.main()