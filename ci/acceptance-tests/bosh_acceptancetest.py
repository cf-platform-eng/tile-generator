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
import sys
import os
import glob
import yaml

class VerifyBoshRelease(unittest.TestCase):

	def test_has_manifest(self):
		self.assertTrue(os.path.exists('release/release.MF'))

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

	def test_form_properties_exist_in_deploy_all(self):
		deploy_all = read_file('release/jobs/deploy-all/templates/deploy-all.sh.erb')
		self.assertIn(b'export AUTHOR=', deploy_all)
		self.assertIn(b'export NATS_HOST=', deploy_all)
		self.assertIn(b'export NATS_HOSTS=', deploy_all)
		self.assertIn(b'export NATS_PROPERTIES=', deploy_all)

	def test_form_properties_exist_in_delete_all(self):
		delete_all = read_file('release/jobs/delete-all/templates/delete-all.sh.erb')
		self.assertIn(b'export AUTHOR=', delete_all)
		self.assertIn(b'export NATS_HOST=', delete_all)
		self.assertIn(b'export NATS_HOSTS=', delete_all)
		self.assertIn(b'export NATS_PROPERTIES=', delete_all)

	# def test_cf_errand_manifest_has_cf_cli_package(self):
	# 	for manifest in glob.glob('release/jobs/*/job.MF'):
	# 		if not manifest.startswith('release/jobs/docker-bosh-'):
	# 			self.assertTrue('cf_cli' in read_yaml(manifest).get('packages', []), manifest)

	# def test_bosh_job_spec_has_no_cf_cli_package(self):
	# 	for manifest in glob.glob('release/jobs/*/job.MF'):
	# 		if manifest.startswith('release/jobs/docker-bosh-'):
	# 			self.assertFalse('cf_cli' in read_yaml(manifest).get('packages', []), manifest)

	def test_all_jobs_have_template(self):
		# 2 templates for each job: one to run the job, and one with the opsmgr env vars.
		self.assertEqual(len(glob.glob('release/jobs/*/templates/*.erb')), 2 * len(glob.glob('release/jobs/*')))

	# def test_has_complete_cf_cli_package(self):
	# 	self.assertEqual(len(glob.glob('release/packages/cf_cli')), 1)
	# 	self.assertEqual(len(glob.glob('release/packages/cf_cli/cf_cli/cf-linux-amd64.tgz')), 1)
	# 	self.assertEqual(len(glob.glob('release/packages/cf_cli/packaging')), 1)
	# 	self.assertTrue('cf-linux-amd64.tgz' in read_file('release/packages/cf_cli/packaging'))

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
