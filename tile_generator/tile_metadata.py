import yaml
from . import template as template_helper

class TileMetadata(object):
    def __init__(self, config):
        self.config = config
        self.tile_metadata = dict()

    def build(self):
        self._build_base()
        self._build_stemcell_criteria()
        self._build_property_blueprints()
        self._build_form_types()
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

    def _build_form_types(self):
        form_types = list()

        # Custom forms from the tile.yml file
        for form in self.config.get('forms', []):
            custom_form = {
                "name": form['name'],
                "label": form['label'],  
                "description": form.get('description') or form.get('label')
            }
            if form.get('markdown'):
                custom_form["markdown"] = str(form['markdown'])

            custom_form["property_inputs"] = list()
            for prop in form.get('properties', []):
                prop_input = {
                    "reference": ".properties." + prop['name'], 
                    "label": prop['label'],
                    "description": prop.get('description') or prop.get('label')
                }
                
                if prop.get('property_blueprints'):
                    prop_input["property_inputs"] = list()
                    for p_input in prop.get('property_blueprints', []):
                        if p_input.get('type') not in ('uuid', 'salted_credentials'):
                            prop_input["property_inputs"].append({
                                "description": p_input.get('description') or p_input.get('label'), 
                                "reference": p_input['name'], 
                                "label": p_input['label']
                            })

                if prop.get('option_templates'):
                    prop_input["selector_property_inputs"] = list()
                    for option in prop.get('option_templates', []):
                        option_dict = {
                            "reference": ".properties.%s.%s" % (prop['name'], option['name']), 
                            "label": option.get('label') or option.get('select_value'),
                        }
                        option_dict["property_inputs"] = list()
                        for p_input in option.get('property_blueprints', []):
                            option_dict_element = {
                                "reference": ".properties.%s.%s.%s" % (prop['name'], option['name'], p_input['name']), 
                                "label": p_input['label']
                            }
                            if p_input.get('description'):
                                option_dict_element["description"] = p_input['description']
                            if p_input.get('placeholder'):
                                option_dict_element["placeholder"] = p_input['placeholder']
                            option_dict["property_inputs"].append(option_dict_element)
                        prop_input["selector_property_inputs"].append(option_dict)
                custom_form["property_inputs"].append(prop_input)
            form_types.append(custom_form)

        # Custom Service Plan forms from the tile.yml file
        for service_plan_form in self.config.get('service_plan_forms', []):
            custom_service_plan_form = {
                "name": service_plan_form['name'],
                "label": service_plan_form['label'], 
                "description": service_plan_form.get('description') or service_plan_form.get('label'),
            }
            if service_plan_form.get('markdown'):
                custom_service_plan_form["markdown"] = str(service_plan_form['markdown']) 

            custom_service_plan_form["property_inputs"] = [{
                "reference": ".properties." + service_plan_form['name'], 
                "label": service_plan_form['label'],
                "property_inputs": [{
                        "label": "Plan Name", 
                        "slug": False, 
                        "reference": "name", 
                        "description": "Name of Plan"
                }]
            }]
            for field in service_plan_form.get('properties', []):
                custom_service_plan_form["property_inputs"][0]["property_inputs"].append({
                    "label": field.get('label') or field.get('name'), 
                    "slug": False, 
                    "reference": field['name'], 
                    "description": field['description']
                })
            form_types.append(custom_service_plan_form)

        # Buildpack form
        buildpack_form = {
            "name": "buildpacks",
            "label": "Buildpack Settings", 
            "description": "Configurable settings for buildpacks",
            "property_inputs": list(),
        }
        for package in [p for p in self.config.get('packages') if p.get('is_buildpack')]:
            buildpack_form["property_inputs"].append({
                "description": "Enter order for the " + (package.get('label') or package.get('name')) + " buildpack", 
                "reference": ".properties." + package.get('name') + "_buildpack_order", 
                "label": (package.get('label') or package.get('name')) + " Buildpack Order",
            })

        if buildpack_form.get("property_inputs"):
            form_types.append(buildpack_form)
                 
                
        # External broker form
        external_broker_form = {
            "name": "external_brokers",
            "label": "Broker Settings", 
            "description": "Configurable settings for external service brokers", 
            "property_inputs": list(),
        }
        for package in [p for p in self.config.get('packages') if p.get('is_external_broker')]:
            external_broker_form["property_inputs"].append(
                {
                    "description": "Enter the External uri/endpoint (with http or https protocol) for the Service Broker", 
                    "reference": ".properties." + package['name'] + "_url", 
                    "label": "Service Broker Application URI for " + (package.get('label') or package.get('name')),
                }, 
                {
                    "description": "Enter the username for accessing the Service Broker", 
                    "reference": ".properties." + package['name'] + "_user", 
                    "label": "Service Broker Username for " + (package.get('label') or package.get('name')),
                }, 
                {
                    "description": "Enter the password for accessing the Service Broker", 
                    "reference": ".properties." + package['name'] + "_password", 
                    "label": "Service Broker Password for " + (package.get('label') or package.get('name')),
                }
            )

        if external_broker_form.get("property_inputs"):
            form_types.append(external_broker_form)

        # Service access form
        service_access_form = {
            "name": "service_access",
            "label": "Service Access", 
            "description": "Determine availability of services",
            "property_inputs": list(),
        }

        for package in [p for p in self.config.get('packages') if p.get('is_broker')]:
            service_access_form["property_inputs"].append({
                "description": "Enable global access to plans in the marketplace", 
                "reference": ".properties." + package['name'] + "_enable_global_access_to_plans", 
                "label": "Enable global access to plans of service " + (package.get('label') or package.get('name')),
            })

        if service_access_form.get("property_inputs"):
            form_types.append(service_access_form)

        # Return value
        self.tile_metadata['form_types'] = form_types

    def _build_runtime_config(self):
        # TODO: this should be making a copy not clobbering the original.
        for runtime_conf in self.config.get('runtime_configs', {}):
            if runtime_conf.get('runtime_config'):
                runtime_conf['runtime_config'] = yaml.dump(runtime_conf['runtime_config'], default_flow_style=False)
        self.tile_metadata['runtime_configs'] = self.config.get('runtime_configs')