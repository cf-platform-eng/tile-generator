import unittest
import sys
import os
import zipfile

class VerifyBoshRelease(unittest.TestCase):

	def test_has_manifest(self):
		self.assertTrue(os.path.exists('release/release.MF'))

if __name__ == '__main__':
	unittest.main()