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


import os
from setuptools import setup
from tile_generator.version import version_string

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

def get_version():
  return version_string


with open('requirements.txt') as f:
  requirements = f.read().splitlines()

setup(
	name = "tile-generator",
	version = get_version(),
	description = 'Tools supporting development of Pivotal Cloud Foundry services and add-ons.',
	long_description=long_description,
  long_description_content_type='text/markdown',
	url = 'https://github.com/cf-platform-eng/tile-generator',
	author = 'Pivotal Cloud Foundry Platform Engineering',
	license = 'Apache 2.0',
	classifiers = [
		'Development Status :: 4 - Beta',
		'Environment :: Console',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: Apache Software License',
		'Programming Language :: Python :: 3 :: Only',
		'Topic :: Software Development',
		'Topic :: Software Development :: Code Generators',
	],
	keywords = [
		'pivotal cloud foundry',
		'tile',
		'generator'
	],
	packages = [ 'tile_generator' ],
	install_requires=requirements,
	include_package_data = True,
	entry_points = {
		'console_scripts': [
			'tile = tile_generator.tile:main',
			'pcf = tile_generator.pcf:main',
		]
	}
)
