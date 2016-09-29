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

from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))
long_description = ''
with open(os.path.join(here, 'README.md')) as f:
    long_descrption = f.read()

setup(
    name = "tile_generator",
    version = "0.9.1",
    description = 'Tools supporting development of Pivotal Cloud Foundry services and add-ons.',
    long_description = long_description,
    url = 'https://github.com/cf-platform-eng/tile-generator',
    author = 'Pivotal Cloud Foundry Platform Engineering',
    license = 'Apache 2.0',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Software Development',
        'Topic :: Software Development :: Code Generators',
    ],
    keywords = [
        'pivotal cloud foundry',
        'tile',
        'generator'
    ],
    packages = [ 'tile_generator' ],
    install_requires = [
        'click>=6.2',
        'Jinja2>=2.8',
        'PyYAML>=3.1',
        'docker-py>=1.6.0',
        'requests>=2.9.1',
        'mock>=2.0.0',
    ],
    include_package_data = True,
    entry_points = {
        'console_scripts': [
            'tile = tile_generator.tile:cli',
            'pcf = tile_generator.pcf:cli',
        ]
    }
)
