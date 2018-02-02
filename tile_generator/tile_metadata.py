import yaml
from . import template as template_helper

class TileMetadata(object):
    def __init__(self, config):
        self.config = config
        self.tile_metadata = dict()

    def build(self):
        self._build_base()
        self._build_stemcell_criteria()
        #self._build_property_blueprints()
        return self.tile_metadata

    def _build_base(self):
        base = {
            'minimum_version_for_upgrade': '0.0.1',
            'rank': 1,
            'serial': True,
        }
        base['name'] = self.config['name']
        base['label'] = self.config['label']
        base['description'] = self.config['description']
        base['icon_image'] = self.config['icon_file']
        base['metadata_version'] = str(self.config['metadata_version'])
        base['service_broker'] = self.config['service_broker']
        self.tile_metadata['base'] = base

    def _build_stemcell_criteria(self):
        stemcell_criteria = dict()
        # Note: tile.py uses self.config['stemcell_criteria']
        stemcell_criteria['os'] = self.config['stemcell_criteria']['os']
        stemcell_criteria['requires_cpi'] = False
        stemcell_criteria['version'] = str(self.config.get('stemcell_criteria', {}).get('version', 3312))
        self.tile_metadata['stemcell_criteria'] = {'stemcell_criteria': stemcell_criteria}

    def _build_property_blueprints(self):
        self.tile_metadata['property_blueprints'] = [
            {
                'configurable': True,
                'default': self.config['org'],
                'name': 'org',
                'type': 'string'
            },
            {
                'configurable': True,
                'default': self.config['space'],
                'name': 'space',
                'type': 'string'
            },
            {
                'configurable': True,
                'default': self.config['apply_open_security_group'],
                'name': 'apply_open_security_group',
                'type': 'boolean'
            },
            {
                'configurable': True,
                'default': self.config['allow_paid_service_plans'],
                'name': 'allow_paid_service_plans',
                'type': 'boolean'
            },
        ]

        if self.config.get('requires_docker_bosh'):
            self.tile_metadata['property_blueprints'].append({
                'configurable': False,
                'name': 'generated_rsa_cert_credentials',
                'optional': False,
                'type': 'rsa_cert_credentials'
            })

        for service_plan_form in self.config['service_plan_forms']:
            #
            # Properties for on-demand service plans
            #
            self.tile_metadata['property_blueprints'].append(
            {
                "type": "collection", 
                "configurable": True, 
                "optional": service_plan_form['optional'] if 'optional' in service_plan_form else True, 
                "name": service_plan_form['name'],
                "property_blueprints": [ 
                    {
                        "type": "uuid", 
                        "unique": True, 
                        "optional": False, 
                        "name": "guid"
                    }, 
                    {
                        "unique": True, 
                        "type": "string", 
                        "name": "name", 
                        "configurable": True
                    }
                ] + service_plan_form['properties']
            }) 

        for release in self.config['releases'].values():
            for package in release.get('packages', []):
                if package.get('is_buildpack'):
                    #
                    # Standard buildpack properties for package {{ package.name }}
                    #
                    self.tile_metadata['property_blueprints'].append(
                      {
                        "default": package.get('buildpack_order') or 99, 
                        "type": "integer", 
                        "name": package['name'] + "_buildpack_order", 
                        "configurable": True
                      }
                    )
                if package.get('is_broker'):
                    #
                    # Standard broker properties for package {{ package.name }}
                    #
                    self.tile_metadata['property_blueprints'].append(
                      {
                        "default": package.get('enable_global_access_to_plans') or 'false', 
                        "type": "boolean", 
                        "name": package['name'] + "_enable_global_access_to_plans", 
                        "configurable": True
                      }
                    )
                if package.get('is_external_broker'):
                    #
                    # Standard external broker properties for package {{ package.name }}
                    #
                    self.tile_metadata['property_blueprints'].append(
                      { 
                        "type": "string", 
                        "name": package['name'] + "_url", 
                        "configurable": True
                      },
                      { 
                        "type": "string", 
                        "name": package['name'] + "_user", 
                        "configurable": True
                      },
                      { 
                        "type": "secret", 
                        "name": package['name'] + "_password", 
                        "configurable": True
                      }
                    )
        #
        # Custom properties from the tile.yml file
        #
        for prop in self.config['all_properties']:
            prop = template_helper.expand_selector(prop)
            self.tile_metadata['property_blueprints'] += [prop]

        return self.tile_metadata

    def _build_runtime_config(self):
        # TODO: this should be making a copy not clobbering the original.
        for runtime_conf in self.config.get('runtime_configs', {}):
            if runtime_conf.get('runtime_config'):
                runtime_conf['runtime_config'] = yaml.dump(runtime_conf['runtime_config'], default_flow_style=False)
        self.tile_metadata['runtime_configs'] = self.config.get('runtime_configs')