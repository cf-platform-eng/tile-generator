import unittest
import build
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

class TestVersionMethods(unittest.TestCase):

	def test_accepts_valid_semver(self):
		self.assertTrue(build.is_semver('11.2.25'))

	def test_rejects_short_semver(self):
		self.assertFalse(build.is_semver('11.2'))

	def test_rejects_long_semver(self):
		self.assertFalse(build.is_semver('11.2.25.3'))

	def test_rejects_non_numeric_semver(self):
		self.assertFalse(build.is_semver('11.2.25dev1'))

	def test_initial_version(self):
		self.assertEquals(build.update_version({}, None), '0.0.1')

	def test_default_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, None), '1.2.4')

	def test_patch_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'patch'), '1.2.4')

	def test_minor_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'minor'), '1.3.0')

	def test_major_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, 'major'), '2.0.0')

	def test_explicit_version_update(self):
		self.assertEquals(build.update_version({ 'version': '1.2.3' }, '5.0.1'), '5.0.1')

	def test_illegal_old_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				build.update_version({ 'version': 'nonsense' }, 'patch')
		self.assertIn('Version must be in semver format', err.getvalue())

	def test_illegal_new_version_update(self):
		with self.assertRaises(SystemExit):
			with capture_output() as (out,err):
				build.update_version({ 'version': '1.2.3' }, 'nonsense')
		self.assertIn('Argument must specify', err.getvalue())

	def test_saves_initial_version(self):
		history = {}
		build.update_version(history, '0.0.1')
		self.assertEquals(history.get('version'), '0.0.1')
		self.assertEquals(len(history.get('history', [])), 0)

	def test_saves_initial_history(self):
		history = { 'version': '0.0.1' }
		build.update_version(history, '0.0.2')
		self.assertEquals(history.get('version'), '0.0.2')
		self.assertEquals(len(history.get('history')), 1)
		self.assertEquals(history.get('history')[0], '0.0.1')

	def test_saves_additional_history(self):
		history = { 'version': '0.0.2', 'history': [ '0.0.1' ] }
		build.update_version(history, '0.0.3')
		self.assertEquals(history.get('version'), '0.0.3')
		self.assertEquals(len(history.get('history')), 2)
		self.assertEquals(history.get('history')[0], '0.0.1')
		self.assertEquals(history.get('history')[1], '0.0.2')

if __name__ == '__main__':
	unittest.main()