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

from __future__ import absolute_import, division, print_function
import errno
import os
import os.path
import requests
import shutil
import sys
import re
import zipfile
try:
	# Python 3
	from urllib.request import urlretrieve
except ImportError:
	# Python 2
	from urllib import urlretrieve

def mkdir_p(dir, clobber=False):
	if clobber and os.path.isdir(dir):
		shutil.rmtree(dir)
	try:
		os.makedirs(dir)
		return dir
	except os.error as e:
		if e.errno != errno.EEXIST:
			raise

def download(url, filename, cache=None):
	if cache is not None:
		basename = os.path.basename(filename)
		cachename = os.path.join(cache, basename)
	 	if os.path.isfile(cachename):
			print('- using cached version of', basename)
			shutil.copy(cachename, filename)
			return
	# Special url to find a file associated with a github release.
	# github://cf-platform-eng/meta-buildpack/meta-buildpack.tgz
	# will find the file named meta-buildpack-0.0.3.tgz in the latest
	# release for https://github.com/cf-platform-eng/meta-buildpack
	if url.startswith("github:"):
		repo_name = url.lstrip("github:").lstrip("/").lstrip("/")
		file_name = os.path.basename(repo_name)
		repo_name = os.path.dirname(repo_name)
		url = "https://api.github.com/repos/" + repo_name + "/releases/latest"
		response = requests.get(url, stream=True)
		response.raise_for_status()
		release = response.json()
		assets = release.get('assets', [])
		url = None
		pattern = re.compile('.*\\.'.join(file_name.rsplit('.', 1))+'\\Z')
		for asset in assets:
			if pattern.match(asset['name']) is not None:
				url = asset['browser_download_url']
				break
		if url is None:
			print('no matching asset found for repo', repo_name, 'file', file_name, file=sys.stderr)
			sys.exit(1)
		# Fallthrough intentional, we now proceed to download the URL we found
	if url.startswith("http:") or url.startswith("https"):
		# [mboldt:20160908] Using urllib.urlretrieve gave an "Access
		# Denied" page when trying to download docker boshrelease.
		# I don't know why. requests.get works. Do what works.
		response = requests.get(url, stream=True)
		response.raise_for_status()
		with open(filename, 'wb') as file:
			for chunk in response.iter_content(chunk_size=1024):
				if chunk:
					file.write(chunk)
	elif url.startswith("docker:"):
		docker_image = url.lstrip("docker:").lstrip("/").lstrip("/")
		try:
			from docker.client import Client
			from docker.utils import kwargs_from_env
			kwargs = kwargs_from_env()
			kwargs['tls'] = False
			docker_cli = Client(**kwargs)
			image = docker_cli.get_image(docker_image)
			image_tar = open(filename,'w')
			image_tar.write(image.data)
			image_tar.close()
		except KeyError as e:
			print('docker not configured on this machine (or environment variables are not properly set)', file=sys.stderr)
			sys.exit(1)
		except:
			print(docker_image, 'not found on local machine', file=sys.stderr)
			print('you must either pull the image, or download it and use the --cache option', file=sys.stderr)
			sys.exit(1)
	elif os.path.isdir(url):
		shutil.copytree(url, filename)
	else:
		shutil.copy(url, filename)

def zip_dir(zipfilename, dirname):
	with zipfile.ZipFile(zipfilename, 'w') as packagezip:
		if os.path.isdir(dirname):
			for root, dirs, files in os.walk(dirname):
				for file in files:
					abspath = os.path.join(root, file)
					relpath = abspath[len(dirname)+1:] # +1 for trailing slash.
					packagezip.write(abspath, relpath)
		elif os.path.isfile(dirname):
			packagezip.write(dirname, os.path.basename(dirname))
