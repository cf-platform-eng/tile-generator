import unittest
import sys
import os
import glob
import yaml

class VerifyTile(unittest.TestCase):

	def test_has_valid_content_migrations(self):
		self.assertTrue(os.path.exists('product/content_migrations'))
		files = glob.glob('product/content_migrations/*.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0]) # Ensure corrent yaml syntax

	def test_has_valid_metadata(self):
		self.assertTrue(os.path.exists('product/metadata'))
		files = glob.glob('product/metadata/*.yml')
		self.assertEqual(len(files), 1)
		read_yaml(files[0]) # Ensure corrent yaml syntax

def read_yaml(filename):
	with open(filename, 'rb') as file:
		return yaml.safe_load(file)

def read_file(filename):
	with open(filename, 'rb') as file:
		return file.read()

if __name__ == '__main__':
	unittest.main()