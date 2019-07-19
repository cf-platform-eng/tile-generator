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

import re
import unittest

import requests

from tile_generator import opsmgr


class VerifyRuntimeConfig(unittest.TestCase):
    def setUp(self):
        self.cfinfo = opsmgr.get_cfinfo()
        self.schema_version = self.cfinfo['schema_version']

    def test_yes(self):
        if re.match(r'1\.+', self.schema_version):
            print("OpsMan is too old to support runtime config, skipping test")
            return

        hostname = 'runtime-conf-yes.' + self.cfinfo['system_domain']
        url = 'http://' + hostname
        response = requests.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.text, r'.*Runtime Test Release: Success.*')

    def test_no(self):
        if re.match(r'1\.+', self.schema_version):
            print("OpsMan is too old to support runtime config, skipping test")
            return

        hostname = 'runtime-conf-no.' + self.cfinfo['system_domain']
        url = 'http://' + hostname
        response = requests.get(url)

        self.assertEqual(response.status_code, 502)
