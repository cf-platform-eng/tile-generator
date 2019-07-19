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
from .tile_metadata import TileMetadata
from .config import Config
from collections import OrderedDict

def find_by_field(field_name, field_value, list_of_dict):
    for d in list_of_dict:
        if field_name in d and field_value == d[field_name]:
            return d

class TestTileMetadata(unittest.TestCase):

    def test_non_configurable_selector_fields_not_in_property_inputs(self):
        forms_with_non_configurable_selector_option = [
            {
                'name': 'form_with_unconfigurable_selector_option',
                'label': 'Form With Unconfigurable Selector Option',
                'description': 'Form With Unconfigurable Selector Option',
                'properties': [
                    {
                        'name': 'selector_with_unconfigurable_option',
                        'label': 'Selector with unconfigurable option',
                        'description': 'This selector has an unconfigurable option',
                        'default': 'unconfigurable_option',
                        'configurable': True,
                        'type': 'selector',
                        'option_templates': [
                            {
                                'name': 'unconfigurable_option',
                                'select_value': 'unconfigurable',
                                'property_blueprints': [
                                    {
                                        'name': 'property_name',
                                        'default': 'unconfigurable_property_value',
                                        'type': 'string',
                                        'label': 'This is not configurable',
                                        'configurable': False,
                                    },
                                ],
                            },
                            {
                                'name': 'configurable_option',
                                'select_value': 'configurable',
                                'property_blueprints': [
                                    {
                                        'name': 'property_name',
                                        'default': 'configurable_property_value',
                                        'type': 'string',
                                        'label': 'This is configurable',
                                        'configurable': True,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ]
        config = Config(name='validname', icon_file='/dev/null', label='some_label', description='This is required', forms=forms_with_non_configurable_selector_option)
        metadata = TileMetadata(config)
        metadata._build_form_types()
        selector_property_inputs = metadata.tile_metadata['form_types'][0]['property_inputs'][0]['selector_property_inputs']
        inputs_with_no_configurable_fields = find_by_field('label', 'unconfigurable', selector_property_inputs)
        self.assertIsNone(inputs_with_no_configurable_fields.get('property_inputs'))

    def test_standalone_tile_excludes_default_cf_blueprints(self):
        config = Config(
            name='validname', 
            icon_file='/dev/null', 
            label='some_label', 
            description='This is required', 
            service_plan_forms=[],
            org='Test Org',
            space='Test Space',
            apply_open_security_group=False,
            allow_paid_service_plans=False,
            releases=OrderedDict(),
            all_properties=[],
            standalone=True)
        metadata = TileMetadata(config)
        metadata._build_property_blueprints()

        expected_blueprints = []
        self.assertEqual(metadata.tile_metadata['property_blueprints'], expected_blueprints)

    def test_non_standalone_tile_includes_default_cf_blueprints(self):
        config = Config(
            name='validname', 
            icon_file='/dev/null', 
            label='some_label', 
            description='This is required', 
            service_plan_forms=[],
            org='Test Org',
            space='Test Space',
            apply_open_security_group=False,
            allow_paid_service_plans=False,
            releases=OrderedDict(),
            all_properties=[])
        metadata = TileMetadata(config)
        metadata._build_property_blueprints()

        expected_blueprints = [
                {
                    'configurable': True,
                    'default': 'Test Org',
                    'name': 'org',
                    'type': 'string'
                },
                {
                    'configurable': True,
                    'default': 'Test Space',
                    'name': 'space',
                    'type': 'string'
                },
                {
                    'configurable': True,
                    'default': False,
                    'name': 'apply_open_security_group',
                    'type': 'boolean'
                },
                {
                    'configurable': True,
                    'default': False,
                    'name': 'allow_paid_service_plans',
                    'type': 'boolean'
                },
            ]

        self.assertEqual(metadata.tile_metadata['property_blueprints'], expected_blueprints)

if __name__ == '__main__':
    unittest.main()
