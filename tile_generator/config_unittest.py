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

import mock
import json
import os
import unittest
import sys
import tempfile
import yaml

from contextlib import contextmanager
from io import StringIO

from . import config
from .config import Config, merge_dict
from .tile_metadata import TileMetadata
from . import template

@contextmanager
def capture_output():
  new_out, new_err = StringIO(), StringIO()
  old_out, old_err = sys.stdout, sys.stderr
  try:
    sys.stdout, sys.stderr = new_out, new_err
    yield sys.stdout, sys.stderr
  finally:
    sys.stdout, sys.stderr = old_out, old_err


class BaseTest(unittest.TestCase):
  def setUp(self):
    self.latest_stemcell_patcher = mock.patch('tile_generator.config.Config.latest_stemcell', return_value='1234')
    self.latest_stemcell = self.latest_stemcell_patcher.start()

    self._update_compilation_vm_disk_size_patcher = mock.patch('tile_generator.config.package_definitions.flag._update_compilation_vm_disk_size', return_value=1234)
    self._update_compilation_vm_disk_size = self._update_compilation_vm_disk_size_patcher.start()

    self.icon_file = tempfile.NamedTemporaryFile()
    self.config = Config(name='validname', icon_file=self.icon_file.name,
                         label='some_label', description='This is required')
    self.pre_start_file = tempfile.NamedTemporaryFile()

  def tearDown(self):
    self.latest_stemcell_patcher.stop()
    self._update_compilation_vm_disk_size_patcher.stop()
    self.icon_file.close()
    self.pre_start_file.close()


@mock.patch('tile_generator.config.Config.read_history')
@mock.patch('tile_generator.config._base64_img')
class TestUltimateForm(BaseTest):
  def test_diff_final_config_obj(self, mock_read_history, mock_base64_img):
    test_path = os.path.dirname(__file__)
    cfg_file_path = os.path.join(test_path, '../sample/tile.yml')

    with mock.patch('tile_generator.config.CONFIG_FILE', cfg_file_path):
      cfg = self.config.read()
    cfg.set_version(None)
    cfg.set_verbose(False)
    cfg.set_sha1(False)
    cfg.set_cache(None)
    
    with open(test_path + '/test_config_generated_output.json', 'w') as f:
      generated_json = json.dumps(cfg, sort_keys=True, indent=2)
      f.write(generated_json)
      generated_output = json.loads(generated_json)

    with open(test_path + '/test_config_expected_output.json', 'r') as f:
      expected_output = json.load(f)
    
    # Change the paths to files to be consistent
    self.fix_path(generated_output)
    self.fix_path(expected_output)

    # Remove keys whose values are dynamic and change with each run
    self.remove_ignored_keys(generated_output)
    self.remove_ignored_keys(expected_output)

    self.deep_comparer(expected_output, generated_output, '[%s]')

    # Ensure there is no extra elements in the generated output
    expected = json.dumps(expected_output, indent=2).split('\n')
    generated = json.dumps(generated_output, indent=2).split('\n')

    self.assertEqual(len(expected), len(generated))
    for line in expected:
      self.assertIn(line, generated)

  def fix_path(self, obj):
    for release in obj['releases'].values():
      for package in release.get('packages', []):
        for f in package.get('files', []):
          if 'tile_generator/templates/src/common/utils.sh' in f.get('path'):
            f['path'] = 'tile_generator/templates/src/common/utils.sh'

  # Remove keys with dynamic values
  def remove_ignored_keys(self, obj):
    ignored_keys = ['history', 'compilation_vm_disk_size', 'version']

    if type(obj) is dict:
      for k,v in list(obj.items()):
        if k in ignored_keys:
          obj.pop(k)
        self.remove_ignored_keys(v)
    if type(obj) is list:
      for item in obj:
        self.remove_ignored_keys(item)    

  def deep_comparer(self, expected, given, path):
    if type(expected) is dict:
      self.assertTrue(type(given) is dict, (path, 
        'Expected to be a dict, but got %s' % type(given)))
      for key in expected.keys():
        self.assertTrue(key in given, 'The key %s is missing' % (path % key))
        self.deep_comparer(expected[key], given[key], path % key + '[%s]')

    elif type(expected) is list:
      total_length = len(expected)
      self.assertTrue(type(given) is list, (path, 
        'Expected to be a list, but got %s' % type(given)))
      self.assertEqual(total_length, len(given), (path, 
        'Expected to have length %s, but got %s' % (total_length, len(given))))
      for index in range(total_length):
        if type(expected[index]) is dict:
          if 'name' in expected[index]:
              given_next = [e for e in given if e.get('name') == expected[index]['name']]
              if not given_next:
                given_next = {}
              else:
                given_next = given_next[0] or {}
          else:
            given_next = given[index]
          self.deep_comparer(expected[index], given_next, path % index + '[%s]')
        elif type(expected[index]) is list:
          expected = sorted(expected)
          given = sorted(given)
          self.deep_comparer(expected[index], given[index], path % index + '[%s]')
        else:
          self.assertIn(expected[index], given, (path % index, 
            'Expected value:\n%s\nIs missing' % expected[index]))

    else:
      try:
        loaded_expected = yaml.load(expected)
        loaded_given = yaml.load(given)
      except:
        loaded_expected = expected
        loaded_given = given

      if type(expected) is str and not type(loaded_expected) is str:
        self.deep_comparer(loaded_expected, loaded_given, path)

      self.assertEqual(expected, given, (path, 
        'Expected to have the value:\n%s\nHowever, instead got:\n%s' % (expected, given)))

  # mock_read_history, mock_base64_img are not used in this method
  def test_metadata_diff(self, mock_read_history, mock_base64_img):
    test_path = os.path.dirname(__file__)
    cfg_file_path = os.path.join(test_path, '../sample/tile.yml')

    with mock.patch('tile_generator.config.CONFIG_FILE', cfg_file_path):
      cfg = self.config.read()
    cfg.set_version(None)
    cfg.set_verbose(False)
    cfg.set_sha1(False)
    cfg.set_cache(None)

    cfg['tile_metadata'] = TileMetadata(cfg).build()
    template.render(test_path + '/test_metadata_generated_output.yml', 'tile/metadata.yml', cfg)

    with open(test_path + '/test_metadata_generated_output.yml', 'r') as f:
      generated_output = yaml.load(f)

    with open(test_path + '/test_metadata_expected_output.yml', 'r') as f:
      expected_output = yaml.load(f)

    self.deep_comparer(expected_output, generated_output, '[%s]')


class TestConfigValidation(BaseTest):
  def test_accepts_minimal_config(self):
    self.config.validate()

  def test_latest_stemcell_config(self):
    # Disable patching latest_stemcell
    self.latest_stemcell_patcher.stop()

    self.config.validate()

    # Enable so that tearDown does not barf
    self.latest_stemcell_patcher.start()

    # Ensure we are using the real latest_stemcell
    self.assertNotEqual(self.config['stemcell_criteria']['version'], '1234')

  def test_requires_package_names(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}, {'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
        self.config.validate()
    self.assertIn("'name': ['required field']", err.getvalue())

  def test_requires_package_types(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}, {'name': 'name'}]
        self.config.validate()
    self.assertIn("has invalid type None\nvalid types are", err.getvalue())

  def test_refuses_invalid_type(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        self.config['packages'] = [{'name': 'validname', 'type': 'nonsense'}]
        self.config.validate()
    self.assertIn("has invalid type nonsense\nvalid types are", err.getvalue())

  def test_accepts_valid_job_name(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'validname'}]}]
    self.config.validate()

  def test_accepts_valid_job_name_with_hyphen(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'valid-name'}]}]
    self.config.validate()

  def test_accepts_valid_job_name_with_underscore(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'valid_name'}]}]
    self.config.validate()

  def test_accepts_valid_job_name_with_number(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'valid2name'}]}]
    self.config.validate()

  def test_accepts_valid_job_name_with_capital(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'validName'}]}]
    self.config.validate()

  def test_accepts_valid_job_name_with_starting_capital(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'Validname'}]}]
    self.config.validate()

  def test_valid_job_memory(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'validname', 'memory': 512}]}]
    self.config.validate()

  def test_invalid_job_memory(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'validname', 'type': 'bosh-release', 'jobs': [{'name': 'validname', 'memory': '512M'}]}]
      self.config.validate()

  def test_accepts_valid_package_name(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()

  def test_accepts_valid_package_name_with_hyphen(self):
    self.config['packages'] = [{'name': 'valid-name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()

  def test_accepts_valid_package_name_with_hyphens(self):
    self.config['packages'] = [{'name': 'valid-name-too', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()

  def test_accepts_valid_package_name_with_number(self):
    self.config['packages'] = [{'name': 'valid-name-2', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()

  def test_refuses_spaces_in_package_name(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'invalid name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
      self.config.validate()

  def test_refuses_capital_letters_in_package_name(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'Invalid', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
      self.config.validate()

  def test_accepts_underscores_in_package_name(self):
    self.config['packages'] = [{'name': 'valid_name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()

  def test_refuses_package_name_starting_with_number(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': '1-invalid-name', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
      self.config.validate()

  def test_refuses_package_name_ending_with_nonalphanumeric(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'invalid-name-', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
      self.config.validate()

    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'invalid-name_', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
      self.config.validate()

  def test_refuses_uppercase_properties_name(self):
    with self.assertRaises(SystemExit):
      self.config['properties'] = [{'name': 'invalidPropName'}]
      self.config.validate()

  def test_refuses_uppercase_form_properties_name(self):
    with self.assertRaises(SystemExit):
      self.config['forms'] = [{
        'label': 'krsna', 
        'properties': [{
          'name': 'invalidFormPropName'
        }],
        'name': 'krsna',
      }]
      self.config.validate()

  def test_requires_product_versions(self):
    self.config['packages'] = [{'name': 'packagename', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}}]
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('requires_product_versions', tile_metadata['base'])
    requires_product_versions = tile_metadata['base']['requires_product_versions']
    self.assertIn('name', requires_product_versions[0])
    self.assertIn('version', requires_product_versions[0])

  def test_manually_addded_requires_product_versions(self):
    self.config['requires_product_versions'] = [{'name': 'cf', 'version': '>= 1.9'}]
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('requires_product_versions', tile_metadata['base'])
    requires_product_versions = tile_metadata['base']['requires_product_versions']
    self.assertIn('name', requires_product_versions[0])
    self.assertIn('version', requires_product_versions[0])

  # This breaks the use case where a user wants to use a local file not in the registry 
  # def test_refuses_docker_bosh_package_without_image(self):
  #   with self.assertRaises(SystemExit):
  #     self.config['packages'] = [{
  #       'name': 'bad_docker_bosh',
  #       'type': 'docker-bosh',
  #       'manifest': 'containers: [name: a]'
  #     }]
  #     self.config.validate()

  def test_accepts_docker_bosh_package_with_image(self):
    self.config['packages'] = [{
      'name': 'good-docker-bosh',
      'type': 'docker-bosh',
      'docker_images': ['my/image'],
      'manifest': 'containers: [name: a]'
    }]
    self.config.validate()

  def test_refuses_docker_bosh_package_without_manifest(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{
        'name': 'bad-docker-bosh',
        'type': 'docker-bosh',
        'docker_images': ['my/image']
      }]
      self.config.validate()

  def test_refuses_docker_bosh_package_with_bad_manifest(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{
        'name': 'bad-docker-bosh',
        'type': 'docker-bosh',
        'docker_images': ['my/image'],
        'manifest': '!^%'
      }]
      self.config.validate()

  def test_validates_docker_bosh_container_names(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{
        'name': 'good-docker-bosh',
        'type': 'docker-bosh',
        'docker_images': ['cholick/foo'],
        'manifest': '''
containers:
- name: bad-name
  image: "cholick/foo"
  bind_ports:
  - '9000:9000'
'''
      }]
      self.config.validate()

  def test_requires_buildpack_for_app_broker(self):
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'packagename', 'type': 'app', 'manifest': {}}]
      self.config.validate()
    with self.assertRaises(SystemExit):
      self.config['packages'] = [{'name': 'packagename', 'type': 'app-broker', 'manifest': {}}]
      self.config.validate()

  def test_buildpack_not_required_for_docker_app(self):
    self.config['packages'] = [{'name': 'packagename', 'type': 'docker-app', 'manifest': {}}]
    self.config.validate()

  def test_error_using_keyword_as_input(self):
    with self.assertRaises(SystemExit):
      self.config['releases'] = ['This should break']
      self.config.validate()

  def test_releases_maintain_order(self):
    self.config['packages'] = [
      { 'name': 'z-name', 'type': 'bosh-release', 'manifest': {}},
      { 'name': 'd-name', 'type': 'bosh-release', 'manifest': {}},
      { 'name': 'a-name', 'type': 'bosh-release', 'manifest': {}},
      { 'name': 'b-name', 'type': 'bosh-release', 'manifest': {}},
    ]
    self.config.validate()
    self.assertEqual([r['name'] for r in self.config['releases'].values()],
      ['z_name', 'd_name', 'a_name', 'b_name'])

class TestVersionMethods(BaseTest):

  def test_accepts_valid_semver(self):
    self.assertTrue(config.is_semver('11.2.25'))

  def test_accepts_valid_semver_with_prerelease(self):
    self.assertTrue(config.is_semver('11.2.25-alpha.1'))

  def test_accepts_valid_semver_with_config(self):
    self.assertTrue(config.is_semver('11.2.25+gb.23'))

  def test_accepts_valid_semver_with_prerelease_and_config(self):
    self.assertTrue(config.is_semver('11.2.25-alpha.1+gb.23'))

  def test_rejects_short_semver(self):
    self.assertFalse(config.is_semver('11.2'))

  def test_rejects_long_semver(self):
    self.assertFalse(config.is_semver('11.2.25.3'))

  def test_rejects_non_numeric_semver(self):
    self.assertFalse(config.is_semver('11.2.25dev1'))

  def test_initial_version(self):
    self.config['history'] = {}
    self.config.set_version(None)
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '0.0.1')
    self.assertEqual(tile_metadata['base']['product_version'], '0.0.1')

  def test_default_version_update(self):
    self.config['history'] = {'version':'1.2.3'}
    self.config.set_version(None)
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '1.2.4')
    self.assertEqual(tile_metadata['base']['product_version'], '1.2.4')

  def test_patch_version_update(self):
    self.config['history'] = {'version':'1.2.3'}
    self.config.set_version('patch')
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '1.2.4')
    self.assertEqual(tile_metadata['base']['product_version'], '1.2.4')

  def test_minor_version_update(self):
    self.config['history'] = {'version':'1.2.3'}
    self.config.set_version('minor')
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '1.3.0')
    self.assertEqual(tile_metadata['base']['product_version'], '1.3.0')

  def test_major_version_update(self):
    self.config['history'] = {'version':'1.2.3'}
    self.config.set_version('major')
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '2.0.0')
    self.assertEqual(tile_metadata['base']['product_version'], '2.0.0')

  def test_explicit_version_update(self):
    self.config['history'] = {'version':'1.2.3'}
    self.config.set_version('5.0.1')
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '5.0.1')
    self.assertEqual(tile_metadata['base']['product_version'], '5.0.1')

  def test_annotated_version_update(self):
    self.config['history'] = {'version':'1.2.3-alpha.1'}
    self.config.set_version('1.2.4')
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(self.config['version'], '1.2.4')
    self.assertEqual(tile_metadata['base']['product_version'], '1.2.4')

  def test_illegal_old_version_update(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        Config(history={'version':'nonsense'}).set_version('patch')
    self.assertIn('prior version must be in semver format', err.getvalue())

  def test_illegal_new_version_update(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        Config(history={'version':'1.2.3'}).set_version('nonsense')
    self.assertIn('Argument must specify', err.getvalue())

  def test_illegal_annotated_version_update(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out,err):
        Config(history={'version':'1.2.3-alpha.1'}).set_version(None)
    self.assertIn('The prior version was 1.2.3-alpha.1', err.getvalue())
    self.assertIn('and must not include a label', err.getvalue())

  def test_saves_initial_version(self):
    history = {}
    Config(history=history).set_version('0.0.1')
    self.assertEqual(history.get('version'), '0.0.1')
    self.assertEqual(len(history.get('history', [])), 0)

  def test_saves_initial_history(self):
    history = { 'version': '0.0.1' }
    Config(history=history).set_version('0.0.2')
    self.assertEqual(history.get('version'), '0.0.2')
    self.assertEqual(len(history.get('history')), 1)
    self.assertEqual(history.get('history')[0], '0.0.1')

  def test_saves_additional_history(self):
    history = { 'version': '0.0.2', 'history': [ '0.0.1' ] }
    Config(history=history).set_version('0.0.3')
    self.assertEqual(history.get('version'), '0.0.3')
    self.assertEqual(len(history.get('history')), 2)
    self.assertEqual(history.get('history')[0], '0.0.1')
    self.assertEqual(history.get('history')[1], '0.0.2')


class TestDefaultOptions(BaseTest):
  def test_purge_service_broker_is_true_by_default(self):
    self.config.update({'name': 'tile-generator-unittest'})
    self.config.validate()
    self.assertTrue(self.config['purge_service_brokers'])

  def test_purge_service_broker_is_overridden(self):
    self.config.update({'purge_service_brokers': False,
         'name': 'tile-generator-unittest'})
    self.config.validate()
    self.assertFalse(self.config['purge_service_brokers'])

  def test_normalize_jobs_default_job_properties(self):
    self.config.update({
      'releases': {'my-job': {
        'jobs': [{
          'name': 'my-job'
        }]
      }}
    })
    self.config.normalize_jobs()
    self.assertEqual(self.config['releases']['my-job']['jobs'][0]['properties'], {})

  def test_default_metadata_version(self):
    self.config.update({'name': 'my-tile'})
    self.config.validate()
    self.assertEqual(self.config['metadata_version'], 1.8)

  def test_default_minimum_version_for_upgrade(self):
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(tile_metadata['base']['minimum_version_for_upgrade'], '0.0.1')

  def test_default_rank(self):
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertEqual(tile_metadata['base']['rank'], 1)

  def test_default_serial(self):
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertTrue(tile_metadata['base']['serial'])

  def test_errands(self):
    self.config['packages'] = [{
      'name': 'some_errand',
      'type': 'bosh-release',
      'path': 'does/it/matter.tgz',
      'jobs': [{
        'name': 'krsna_job',
        'templates': [{'name': 'krsna', 'release': 'blah',
          'post_deploy': True,
          'pre_delete': True,
          'colocated': True,
          'run_default': 'off',
          'instances': ['some_vm/first'],
          'label': 'colocated errand X',
          'description': 'This is a test errand'}]
      }]
    }]
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    expected = [{'colocated': True, 'run_default': 'off', 
                'description': 'This is a test errand', 
                'name': 'krsna', 'label': 'colocated errand X',
                'instances': ['some_vm/first']}]
    self.assertEqual(tile_metadata['post_deploy_errands'], expected)
    self.assertEqual(tile_metadata['pre_delete_errands'], expected)

  def test_multiline_yaml(self):
    self.config['forms'] = [{'label': 'Compatibility', 
      'properties': [{'description': 'Enable compatibility with the GCP Service Broker v3.x.\n\
Before version 4.0, each installation generated its own plan UUIDs, after 4.0 they have been standardized.\n\
This option installs a compatibility layer which checks if a service is using the correct plan GUID.\n\
If the service does not use the correct GUID, the request will fail with a message about how to upgrade.', 
        'name': 'gsb_compatibility_three_to_four',
        'default': False,
        'optional': False, 
        'configurable': True,
        'type': 'boolean',
        'label': 'Compatibility with GCP Service Broker v3.X'
      }], 
      'name': 'compatibility',
      'description': 'Legacy Compatibility Options'
    }]
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    expected = 'Enable compatibility with the GCP Service Broker v3.x.\n\
Before version 4.0, each installation generated its own plan UUIDs, after 4.0 they have been standardized.\n\
This option installs a compatibility layer which checks if a service is using the correct plan GUID.\n\
If the service does not use the correct GUID, the request will fail with a message about how to upgrade.'
    self.assertEqual(tile_metadata['form_types'][0]['property_inputs'][0]['description'], expected)

  def test_standalone_job_type(self):
    self.config.update({
      'packages': [{
        'name': 'some_errand',
        'type': 'bosh-release',
        'path': 'does/it/matter.tgz',
        'jobs': [{
          'name': 'my-job',
          'type': 'standalone'
        }]
      }]
    })
    self.config.validate()
    self.config.normalize_jobs()
    expected = {
      'some_errand': {
        'name': 'some_errand'
      }
    }

    self.assertEqual(self.config['releases']['some_errand']['jobs'][0]['manifest'], expected)

  def test_deploy_all_job_type_with_external_broker(self):
    self.config.update({
      'packages': [{
        'name': 'some_errand',
        'type': 'external-broker',
        'path': 'does/it/matter.tgz',
        'jobs': [{
          'name': 'my-job',
          'type': 'deploy-all'
        }]
      }]
    })

    expected = {
      'security': {
        'user': '(( .deploy-all.app_credentials.identity ))',
        'password': '(( .deploy-all.app_credentials.password ))',
      },
      'some_errand': {
        'name': 'some_errand',
        'url': '(( .properties.some_errand_url.value ))',
        'enable_global_access_to_plans': '(( .properties.some_errand_enable_global_access_to_plans.value ))',
        'user': '(( .properties.some_errand_user.value ))',
        'password': '(( .properties.some_errand_password.value ))',
      }
    }
    merge_dict(expected, Config.cf_job_manifest_properties())

    self.config.validate()
    self.config.normalize_jobs()

    self.assertEqual(self.config['releases']['validname']['jobs'][0]['manifest'], expected)

  def test_deploy_all_job_type_with_broker(self):
    self.config.update({
      'packages': [{
        'name': 'some_errand',
        'type': 'app-broker',
        'path': 'does/it/matter.tgz',
        'jobs': [{
          'name': 'my-job',
          'type': 'deploy-all'
        }],
        'manifest': {
          'buildpack': 'app_buildpack', 
          'path': 'foo'
        }
      }]
    })

    self.config.validate()
    self.config.normalize_jobs()

    expected = {
      'security': {
        'user': '(( .deploy-all.app_credentials.identity ))',
        'password': '(( .deploy-all.app_credentials.password ))',
      },
      'some_errand': {
        'name': 'some_errand',
        'enable_global_access_to_plans': '(( .properties.some_errand_enable_global_access_to_plans.value ))',
        'user': '(( .deploy-all.app_credentials.identity ))',
        'password': '(( .deploy-all.app_credentials.password ))',
        'app_manifest': {
          'path': 'foo',
          'buildpack': 'app_buildpack'
        },
        'auto_services': []
      }
    }
    merge_dict(expected, Config.cf_job_manifest_properties())

    self.assertEqual(self.config['releases']['validname']['jobs'][0]['manifest'], expected)

  def test_deploy_charts_job_type(self):
    self.config.update({
      'packages': [{
        'name': 'some_errand',
        'type': 'bosh-release',
        'path': 'does/it/matter.tgz',
        'jobs': [{
          'name': 'my-job',
          'type': 'deploy-charts'
        }]
      }]
    })
    self.config.validate()
    self.config.normalize_jobs()
    
    expected = {
      'some_errand': {
        'name': 'some_errand'
      },
      'pks_username': '(( ..pivotal-container-service.properties.pks_basic_auth.identity ))',
      'pks_password': '(( ..pivotal-container-service.properties.pks_basic_auth.password ))',
    }
    merge_dict(expected, Config.cf_job_manifest_properties())

    self.assertEqual(self.config['releases']['some_errand']['jobs'][0]['manifest'], expected)

  def test_no_type_job(self):
    self.config.update({
      'packages': [{
        'name': 'some_errand',
        'type': 'bosh-release',
        'path': 'does/it/matter.tgz',
        'jobs': [{
          'name': 'my-job',
        }]
      }]
    })
    self.config.validate()
    self.config.normalize_jobs()
    
    expected = {
      'some_errand': {
        'name': 'some_errand'
      },
    }
    merge_dict(expected, Config.cf_job_manifest_properties())

    self.assertEqual(self.config['releases']['some_errand']['jobs'][0]['manifest'], expected)

@mock.patch('os.path.getsize')
class TestVMDiskSize(BaseTest):
  def test_min_vm_disk_size(self, mock_getsize):
    # Don't patch _update_compilation_vm_disk_size_patcher
    self._update_compilation_vm_disk_size_patcher.stop()
    mock_getsize.return_value = 0
    self.config.update({'name': 'tile-generator-unittest'})
    self.config['packages'] = [{
      'name': 'validname', 'type': 'app',
      'manifest': {'buildpack': 'app_buildpack', 'path': 'foo'}
    }]
    expected_size = 10240
    with mock.patch('os.path.exists',return_value = True):
      self.config.validate()

    # Start so teardown does not break
    self._update_compilation_vm_disk_size_patcher.start()
    self.assertEqual(self.config['compilation_vm_disk_size'], expected_size)

  def test_big_default_vm_disk_size(self, mock_getsize):
    # Don't patch _update_compilation_vm_disk_size_patcher
    self._update_compilation_vm_disk_size_patcher.stop()
    self.config.update({'name': 'tile-generator-unittest'})
    self.config['packages'] = [{
      'name': 'validname', 'type': 'app',
      'manifest': {'buildpack': 'app_buildpack', 'path': 'foo'}
    }]
    default_package_size = 10240
    mock_getsize.return_value = default_package_size * 1024 * 1024 # megabytes to bytes.
    expected_size = 4 * default_package_size
    with mock.patch('os.path.exists', return_value=True):
      self.config.validate()

    # Start so teardown does not break
    self._update_compilation_vm_disk_size_patcher.start()
    self.assertEqual(self.config['compilation_vm_disk_size'], expected_size)

class TestTileName(BaseTest):
  def test_process_name_sets_name_in_tile_metadata(self):
    name = 'my-tile'
    self.config.update({'name': name})
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('name', tile_metadata['base'])
    self.assertEqual(tile_metadata['base']['name'], name)

  def test_requires_product_name(self):
    with self.assertRaises(SystemExit):
      self.config.pop('name')
      self.config.validate()

  def test_accepts_valid_product_name_with_hyphen(self):
    self.config.update({'name': 'valid-name'})
    self.config.validate()

  def test_accepts_valid_product_name_with_hyphens(self):
    self.config.update({'name': 'valid-name-too'})
    self.config.validate()

  def test_accepts_valid_product_name_with_number(self):
    self.config.update({'name': 'valid-name-2'})
    self.config.validate()

  def test_accepts_valid_product_name_with_one_letter_prefix(self):
    self.config.update({'name': 'p-tile'})
    self.config.validate()

  def test_refuses_spaces_in_product_name(self):
    with self.assertRaises(SystemExit):
      self.config.update({'name': 'an invalid name'})
      self.config.validate()

  def test_refuses_capital_letters_in_product_name(self):
    with self.assertRaises(SystemExit):
      self.config.update({'name': 'Invalid'})
      self.config.validate()

  def test_accepts_underscores_in_product_name(self):
    self.config.update({'name': 'valid_name'})
    self.config.validate()

  def test_refuses_product_name_starting_with_number(self):
    with self.assertRaises(SystemExit):
      self.config.update({'name': '1-invalid-name'})
      self.config.validate()

  def test_refuses_product_name_ending_with_nonalphanumeric(self):
    with self.assertRaises(SystemExit):
      self.config.update({'name': 'invalid-name-'})
      self.config.validate()

    with self.assertRaises(SystemExit):
      self.config.update({'name': 'invalid-name_'})
      self.config.validate()

class TestTileSimpleFields(BaseTest):
  def test_requires_label(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out, err):
        self.config.pop('label')
        self.config.validate()
    self.assertIn('label', err.getvalue())

  def test_sets_label(self):
    self.config.update({'label': 'my-label'})
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('label', tile_metadata['base'])
    self.assertEqual(tile_metadata['base']['label'], 'my-label')

  def test_requires_description(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out, err):
        self.config.pop('description')
        self.config.validate()
    self.assertIn('description', err.getvalue())

  def test_sets_description(self):
    self.config.update({'description': 'my tile description'})
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('description', tile_metadata['base'])
    self.assertEqual(tile_metadata['base']['description'], 'my tile description')

  def test_sets_metadata_version(self):
    self.config.update({'metadata_version': 1.8})
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('metadata_version', tile_metadata['base'])
    self.assertEqual(tile_metadata['base']['metadata_version'], '1.8')

  def test_sets_service_broker(self):
    self.config.update({'service_broker': True})
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('service_broker', tile_metadata['base'])
    self.assertTrue(tile_metadata['base']['service_broker'])


class TestTileIconFile(BaseTest):
  def test_requires_icon_file(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out, err):
        cfg = Config({})
        cfg.validate()
    self.assertIn('icon_file', err.getvalue())

  def test_refuses_empty_icon_file(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out, err):
        self.config['icon_file'] = None
        self.config.validate()
    self.assertIn('icon_file', err.getvalue())

  def test_refuses_invalid_icon_file(self):
    with self.assertRaises(SystemExit):
      with capture_output() as (out, err):
        self.config['icon_file'] = '/this/file/does/not/exist'
        self.config.validate()
    self.assertIn('icon_file', err.getvalue())

  def test_sets_icon_image(self):
    self.icon_file.write(b'foo')
    self.icon_file.flush()
    self.config.validate()
    tile_metadata = TileMetadata(self.config).build()
    self.assertIn('icon_image', tile_metadata['base'])
    # Base64-encoded string from `echo -n foo | base64`
    self.assertEqual(tile_metadata['base']['icon_image'], 'Zm9v')

class TestPreStartFile(BaseTest):
  def test_loads_pre_start_file(self):
    self.config['packages'] = [{'name': 'validname', 'type': 'app', 'manifest': {'buildpack': 'app_buildpack'}, 'pre_start_file': self.pre_start_file.name }]
    self.pre_start_file.write(b'some prestart code')
    self.pre_start_file.flush()
    self.config.validate()
    self.assertEqual(self.config['packages'][0]['pre_start'], 'some prestart code')


if __name__ == '__main__':
  unittest.main()
