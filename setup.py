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
setup(
    name = "tile_generator",
    version = "0.9.1",
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
