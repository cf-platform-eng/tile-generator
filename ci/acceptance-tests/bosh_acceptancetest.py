import unittest
import sys
import os

class VerifyBoshRelease(unittest.TestCase):

	def test_has_valid_config_final(self):
		self.assertTrue(os.path.exists('release/config/final.yml'))

if __name__ == '__main__':
	unittest.main()