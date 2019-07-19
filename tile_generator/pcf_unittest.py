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
import mock
import requests
from io import BytesIO
from .pcf import bosh_env_cmd
from click.testing import CliRunner


def build_response(body, encoding='application/json', status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response.encoding = encoding
    response.raw = BytesIO(body)
    response.request = requests.Request()
    response.request.url = 'https://example.com/'
    return response


@mock.patch('tile_generator.opsmgr.get')
class TestBoshEnvCmd(unittest.TestCase):
    def test_pcf_2_2_uses_jobs(self, mock_get):
        mock_get.side_effect = [
            build_response(opsmgr_responses['/api/v0/deployed/director/credentials/director_credentials']),
            build_response(opsmgr_responses['2.2 /api/v0/deployed/director/manifest'])
        ]

        # Since bosh_env_cmd is wrapped by a @cli.command, we need to invoke it this way
        runner = CliRunner()
        result = runner.invoke(bosh_env_cmd, [])

        self.assertIn('BOSH_ENVIRONMENT="10.0.0.5"', result.output)
        self.assertIn('BOSH_CA_CERT="/var/tempest/workspaces/default/root_ca_certificate"', result.output)
        self.assertIn('BOSH USERNAME=director', result.output)
        self.assertIn('BOSH PASSWORD=super-secret-password', result.output)

    def test_pcf_2_3_uses_instance_groups(self, mock_get):
        mock_get.side_effect = [
            build_response(opsmgr_responses['/api/v0/deployed/director/credentials/director_credentials']),
            build_response(opsmgr_responses['2.3 /api/v0/deployed/director/manifest'])
        ]

        # Since bosh_env_cmd is wrapped by a @cli.command, we need to invoke it this way
        runner = CliRunner()
        result = runner.invoke(bosh_env_cmd, [])

        self.assertIn('BOSH_ENVIRONMENT="10.0.0.6"', result.output)
        self.assertIn('BOSH_CA_CERT="/var/tempest/workspaces/default/root_ca_certificate"', result.output)
        self.assertIn('BOSH USERNAME=director', result.output)
        self.assertIn('BOSH PASSWORD=super-secret-password', result.output)


if __name__ == '__main__':
    unittest.main()

opsmgr_responses = {}
opsmgr_responses['/api/v0/deployed/director/credentials/director_credentials'] = b"""{
  "credential": {
    "type": "simple_credentials",
    "value": {
      "password": "super-secret-password",
      "identity": "director"
    }
  }
}"""
opsmgr_responses['2.2 /api/v0/deployed/director/manifest'] = b"""{
  "jobs": [ { "properties": { "director": { "address": "10.0.0.5" } } } ]
}"""
opsmgr_responses['2.3 /api/v0/deployed/director/manifest'] = b"""{
  "instance_groups": [ { "properties": { "director": { "address": "10.0.0.6" } } } ]
}"""
