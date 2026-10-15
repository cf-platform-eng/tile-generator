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
from .pcf import bosh_env_cmd, install_cmd, uninstall_cmd, settings_cmd
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


staged_products = b"""[
    {"installation_name": "cf-36f9d85a723246da59ef", "guid": "cf-36f9d85a723246da59ef", "type": "cf", "product_version": "10.3.7"},
    {"installation_name": "test-tile-0123456789abcdef0123", "guid": "test-tile-0123456789abcdef0123", "type": "test-tile", "product_version": "1.0.0"}
]"""


@mock.patch('tile_generator.opsmgr.get_products')
class TestInstallCmd(unittest.TestCase):
    @mock.patch('tile_generator.opsmgr.post_json')
    def test_new_product_is_staged(self, mock_post_json, mock_get_products):
        mock_get_products.return_value = [{'name': 'test-tile', 'product_version': '1.0.0', 'installed': False}]
        result = CliRunner().invoke(install_cmd, ['test-tile', '1.0.0'])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_post_json.assert_called_once_with('/api/v0/staged/products', {'name': 'test-tile', 'product_version': '1.0.0'})

    @mock.patch('tile_generator.opsmgr.put_json')
    def test_staged_product_is_upgraded(self, mock_put_json, mock_get_products):
        mock_get_products.return_value = [{'name': 'test-tile', 'product_version': '1.0.0', 'installed': True, 'guid': 'test-tile-0123456789abcdef0123'}]
        mock_put_json.return_value = build_response(b'{}')
        result = CliRunner().invoke(install_cmd, ['test-tile', '1.1.0'])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_put_json.assert_called_once_with('/api/v0/staged/products/test-tile-0123456789abcdef0123', {'to_version': '1.1.0'}, check=False)

    @mock.patch('tile_generator.opsmgr.put_json')
    def test_already_installed_version(self, mock_put_json, mock_get_products):
        mock_get_products.return_value = [{'name': 'test-tile', 'product_version': '1.0.0', 'installed': True, 'guid': 'test-tile-0123456789abcdef0123'}]
        mock_put_json.return_value = build_response(b'{"errors": ["Version 1.0.0 is already in use."]}', status_code=422)
        result = CliRunner().invoke(install_cmd, ['test-tile', '1.0.0'])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('version already installed', result.output)


@mock.patch('tile_generator.opsmgr.delete')
@mock.patch('tile_generator.opsmgr.get')
class TestUninstallCmd(unittest.TestCase):
    def test_deletes_matching_staged_product(self, mock_get, mock_delete):
        mock_get.return_value = build_response(staged_products)
        result = CliRunner().invoke(uninstall_cmd, ['test-tile'])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_get.assert_called_once_with('/api/v0/staged/products')
        mock_delete.assert_called_once_with('/api/v0/staged/products/test-tile-0123456789abcdef0123')

    def test_version_mismatch_is_kept(self, mock_get, mock_delete):
        mock_get.return_value = build_response(staged_products)
        result = CliRunner().invoke(uninstall_cmd, ['test-tile', '2.0.0'])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_delete.assert_not_called()


@mock.patch('tile_generator.opsmgr.get')
class TestSettingsCmd(unittest.TestCase):
    def test_lists_staged_products(self, mock_get):
        mock_get.return_value = build_response(staged_products)
        result = CliRunner().invoke(settings_cmd, [])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('test-tile-0123456789abcdef0123', result.output)

    def test_shows_product_properties(self, mock_get):
        mock_get.side_effect = [
            build_response(staged_products),
            build_response(b'{"properties": {".properties.author": {"value": "Tile Ninja"}}}'),
        ]
        result = CliRunner().invoke(settings_cmd, ['test-tile'])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_get.assert_called_with('/api/v0/staged/products/test-tile-0123456789abcdef0123/properties')
        self.assertIn('Tile Ninja', result.output)

    def test_unknown_product(self, mock_get):
        mock_get.return_value = build_response(staged_products)
        result = CliRunner().invoke(settings_cmd, ['missing-tile'])
        self.assertEqual(result.exit_code, 1)


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
