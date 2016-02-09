import unittest
import sys
import os
import glob
import yaml

class VerifyBoshRelease(unittest.TestCase):

	def test_has_manifest(self):
		self.assertTrue(os.path.exists('release/release.MF'))

	def test_has_correct_number_of_jobs(self):
		self.assertEqual(len(glob.glob('release/jobs/*')), 17)

	def test_has_correct_number_of_app_jobs(self):
		self.assertEqual(len(glob.glob('release/jobs/deploy-app-*')), 5)
		self.assertEqual(len(glob.glob('release/jobs/delete-app-*')), 5)

	def test_has_correct_number_of_broker_jobs(self):
		self.assertEqual(len(glob.glob('release/jobs/register-broker-*')), 2)
		self.assertEqual(len(glob.glob('release/jobs/destroy-broker-*')), 2)

	def test_has_correct_number_of_buildpack_jobs(self):
		self.assertEqual(len(glob.glob('release/jobs/deploy-buildpack-*')), 1)
		self.assertEqual(len(glob.glob('release/jobs/delete-buildpack-*')), 1)

	def test_has_correct_number_of_docker_jobs(self):
		self.assertEqual(len(glob.glob('release/jobs/docker-bosh-*')), 1)

	def test_all_jobs_have_monit(self):
		self.assertEqual(len(glob.glob('release/jobs/*/monit')), len(glob.glob('release/jobs/*')))

	def test_errands_have_empty_monit(self):
		for monit in glob.glob('release/jobs/*/monit'):
			if not monit.startswith('release/jobs/docker-bosh-'):
				self.assertTrue(os.path.exists(monit), monit)
				self.assertEqual(os.path.getsize(monit), 0, monit)

	def test_non_errands_have_nonempty_monit(self):
		for monit in glob.glob('release/jobs/*'):
			if monit.startswith('release/jobs/docker-bosh-'):
				self.assertTrue(os.path.exists(monit), monit)
				self.assertNotEqual(os.path.getsize(monit), 0, monit)

	def test_all_jobs_have_manifest(self):
		self.assertEqual(len(glob.glob('release/jobs/*/job.MF')), len(glob.glob('release/jobs/*')))

	def test_cf_errand_manifest_has_cf_cli_package(self):
		for manifest in glob.glob('release/jobs/*/job.MF'):
			if not manifest.startswith('release/jobs/docker-bosh-'):
				self.assertTrue('cf_cli' in read_yaml(manifest).get('packages', []), manifest)

	def test_bosh_job_spec_has_no_cf_cli_package(self):
		for manifest in glob.glob('release/jobs/*/job.MF'):
			if manifest.startswith('release/jobs/docker-bosh-'):
				self.assertFalse('cf_cli' in read_yaml(manifest).get('packages', []), manifest)

	def test_all_jobs_have_template(self):
		self.assertEqual(len(glob.glob('release/jobs/*/templates/*.sh.erb')), len(glob.glob('release/jobs/*')))

	def test_has_correct_number_of_packages(self):
		self.assertEqual(len(glob.glob('release/packages/*')), 9)

	def test_has_complete_cf_cli_package(self):
		self.assertEqual(len(glob.glob('release/packages/cf_cli')), 1)
		self.assertEqual(len(glob.glob('release/packages/cf_cli/cf_cli/cf-linux-amd64.tgz')), 1)
		self.assertEqual(len(glob.glob('release/packages/cf_cli/packaging')), 1)
		self.assertTrue('cf-linux-amd64.tgz' in read_file('release/packages/cf_cli/packaging'))

	def test_has_complete_common_package(self):
		self.assertEqual(len(glob.glob('release/packages/common')), 1)
		self.assertEqual(len(glob.glob('release/packages/common/common/utils.sh')), 1)

def read_yaml(filename):
	with open(filename, 'rb') as file:
		return yaml.safe_load(file)

def read_file(filename):
	with open(filename, 'rb') as file:
		return file.read()

if __name__ == '__main__':
	unittest.main()