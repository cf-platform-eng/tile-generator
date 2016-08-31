#!/usr/bin/env python

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

class BoshReleases:

	def __init__(self, releases_dir):
		self.releases_dir = releases_dir
		self.known_releases = {}

	def get(release_name, create=False):
		release = known_releases.get(release_name, None)
		if release is not None:
			return release
		release = BoshRelease.create(release_name, os.path.join(self.releases_dir, release_name))
		self.known_releases[release_name] = release
		return release

	def list():
		return known_releases.itervalues()

class BoshRelease:

	def create(release_name, release_dir):
		return BoshRelease(release_name, release_dir).init()

	def __init__(self, release_name, release_dir):
		self.release_name = release_name
		self.release_dir = release_dir
		self.post_deploy_errands = []
		self.pre_delete_errands = []

	def init(self):
		self.__bosh('init', 'release')
		self.__render('config/final.yml', 'config/final.yml', context)
		return self

	def add_bosh_job(context, package, job_type, post_deploy=False, pre_delete=False):
		is_errand = post_deploy or pre_delete
		job_name = job_type
		if package is not None:
			job_name += '-' + package['name']

		self.__bosh('generate', 'job', job_name)
		job_context = {
			'job_name': job_name,
			'job_type': job_type,
			'context': context,
			'package': package,
			'errand': is_errand,
		}
		self.__render(
			os.path.join('jobs', job_name, 'spec'),
			os.path.join('jobs', 'spec'),
			job_context
		)
		self.__render(
			os.path.join('jobs', job_name, 'templates', job_name + '.sh.erb'),
			os.path.join('jobs', job_type + '.sh.erb'),
			job_context
		)
		self.__render(
			os.path.join('jobs', job_name, 'monit'),
			os.path.join('jobs', 'monit'),
			job_context
		)

		context['jobs'] = context.get('jobs', []) + [{
			'name': job_name,
			'type': job_type,
			'package': package,
		}]
		if post_deploy:
			self.post_deploy_errands += [{ 'name': job_name }]
		if pre_delete:
			self.pre_delete_errands += [{ 'name': job_name }]

	def add_src_package(context, package, alternate_template=None):
		add_package('src', context, package, alternate_template)

	def add_blob_package(context, package, alternate_template=None):
		add_package('blobs', context, package, alternate_template)

	def add_package(dir, context, package, alternate_template=None):
		name = package['name'].lower().replace('-','_')
		package['name'] = name
		bosh('generate', 'package', name)
		target_dir = os.path.realpath(os.path.join(dir, name))
		package_dir = os.path.realpath(os.path.join('packages', name))
		mkdir_p(target_dir)
		template_dir = 'packages'
		if alternate_template is not None:
			template_dir = os.path.join(template_dir, alternate_template)
		package_context = {
			'context': context,
			'package': package,
			'files': []
		}
		with cd('..'):
			files = package.get('files', [])
			path = package.get('path', None)
			if path is not None:
				files += [ { 'path': path } ]
				package['path'] = os.path.basename(path)
			manifest = package.get('manifest', None)
			manifest_path = None
			if type(manifest) is dict:
				manifest_path = manifest.get('path', None)
			if manifest_path is not None:
				files += [ { 'path': manifest_path } ]
				package['manifest']['path'] = os.path.basename(manifest_path)
			for file in files:
				filename = file.get('name', os.path.basename(file['path']))
				file['name'] = filename
				urllib.urlretrieve(file['path'], os.path.join(target_dir, filename))
				package_context['files'] += [ filename ]
			for docker_image in package.get('docker_images', []):
				filename = docker_image.lower().replace('/','-').replace(':','-') + '.tgz'
				download_docker_image(docker_image, os.path.join(target_dir, filename), cache=context.get('docker_cache', None))
				package_context['files'] += [ filename ]
		if package.get('is_app', False):
			manifest = package.get('manifest', { 'name': name })
			if manifest.get('random-route', False):
				print >> sys.stderr, 'Illegal manifest option in package', name + ': random-route is not supported'
				sys.exit(1)
			manifest_file = os.path.join(target_dir, 'manifest.yml')
			with open(manifest_file, 'wb') as f:
				f.write('---\n')
				f.write(yaml.safe_dump(manifest, default_flow_style=False))
			package_context['files'] += [ 'manifest.yml' ]
			update_memory(context, manifest)
		template.render(
			os.path.join(package_dir, 'spec'),
			os.path.join(template_dir, 'spec'),
			package_context
		)
		template.render(
			os.path.join(package_dir, 'packaging'),
			os.path.join(template_dir, 'packaging'),
			package_context
		)

	def __bosh(self, *argv):
		argv = list(argv)
		print 'bosh', ' '.join(argv)
		command = [ 'bosh', '--no-color', '--non-interactive' ] + argv
		try:
			return subprocess.check_output(command, stderr=subprocess.STDOUT, cwd=self.release_dir)
		except subprocess.CalledProcessError as e:
			if argv[0] == 'init' and argv[1] == 'release' and 'Release already initialized' in e.output:
				return e.output
			if argv[0] == 'generate' and 'already exists' in e.output:
				return e.output
			print e.output
			sys.exit(e.returncode)

	def __render(self, template, target, context):
		template.render(template, os.path.join(self.release_dir, target), context)
