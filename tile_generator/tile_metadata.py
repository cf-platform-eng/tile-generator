import yaml
from . import template as template_helper


# Inspired by: https://stackoverflow.com/questions/6432605/any-yaml-libraries-in-python-that-support-dumping-of-long-strings-as-block-liter
class literal_unicode(unicode): pass
def literal_unicode_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
yaml.SafeDumper.add_representer(literal_unicode, literal_unicode_representer)


class TileMetadata(object):
    def __init__(self, config):
        self.config = config
        self.tile_metadata = dict()

    def build(self):
        self._build_base()
        self._build_stemcell_criteria()
        self._build_property_blueprints()
        self._build_form_types()
        self._build_job_types()
        self._build_runtime_config()
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

        base['product_version'] = str(self.config.get('version'))
        product_versions = list()
        for k, v in self.config.get('requires_product_versions', {}).items():
            product_versions.append({
                'name': k,
                'version': v,
                })
        if product_versions: 
            base['requires_product_versions'] = product_versions

        for key in self.config.get('unknown_keys', []):
            base[key] = self.config[key]

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
                        "default": package.get('enable_global_access_to_plans') or False, 
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
                    if not prop_input["property_inputs"]: prop_input["property_inputs"] = None

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
                        if not option_dict["property_inputs"]: option_dict["property_inputs"] = None
                        prop_input["selector_property_inputs"].append(option_dict)
                custom_form["property_inputs"].append(prop_input)
            if not custom_form["property_inputs"]: custom_form["property_inputs"] = None
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
        for package in [p for p in self.config.get('packages', []) if p.get('is_buildpack')]:
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
        for package in [p for p in self.config.get('packages', []) if p.get('is_external_broker')]:
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

        for package in [p for p in self.config.get('packages', []) if p.get('is_broker')]:
            service_access_form["property_inputs"].append({
                "description": "Enable global access to plans in the marketplace", 
                "reference": ".properties." + package['name'] + "_enable_global_access_to_plans", 
                "label": "Enable global access to plans of service " + (package.get('label') or package.get('name')),
            })

        if service_access_form.get("property_inputs"):
            form_types.append(service_access_form)

        # Return value
        self.tile_metadata['form_types'] = form_types

    def _build_job_types(self):
        job_types = list()
        # Default compilation job
        if self.config['metadata_version'] < 1.8:
            compilation_job = {
                "dynamic_ip": 1, 
                "max_in_flight": 1, 
                "name": "compilation", 
                "single_az_only": True, 
                "resource_label": "compilation", 
                "resource_definitions": [
                {
                    "default": 4096, 
                    "type": "integer", 
                    "name": "ram", 
                    "configurable": True
                }, 
                {
                    "default": self.config.get("compilation_vm_disk_size"), 
                    "type": "integer", 
                    "name": "ephemeral_disk", 
                    "configurable": True
                }, 
                {
                    "default": 0, 
                    "type": "integer", 
                    "name": "persistent_disk", 
                    "configurable": True
                }, 
                {
                    "default": 2, 
                    "type": "integer", 
                    "name": "cpu", 
                    "configurable": True
                }
                ], 
                "static_ip": 0
            }
            instance_def = {
                'configurable': True,
                'default': 1,
                'name': 'instances',
                'type': 'integer'
            }
            if self.config['metadata_version'] < 1.7:
                compilation_job['instance_definitions'] = [instance_def]
            else:
                compilation_job['instance_definition'] = instance_def

            job_types.append(compilation_job)


        #
        # {{ job.template }} job for {{ job.package.name }}
        #
        for release in self.config.get('releases', {}).values():
            for job in [j for j in release.get('jobs', []) if j.get('template') and j.get('template') == 'docker-bosh']:
                release_job = {
                    'dynamic_ip': 0,
                    'errand': False,
                    'max_in_flight': 1,
                    'name': job.get('name'),
                    'resource_definitions': [
                        {'configurable': True,
                        'constraints': {'min': job.get('package').get('memory')},
                        'default': job.get('package').get('memory'),
                        'name': 'ram',
                        'type': 'integer'},
                        {'configurable': True,
                        'constraints': {'min': job.get('package').get('ephemeral_disk')},
                        'default': job.get('package').get('ephemeral_disk'),
                        'name': 'ephemeral_disk',
                        'type': 'integer'},
                        {'configurable': True,
                        'constraints': {'min': job.get('package').get('persistent_disk', 0)},
                        'default': job.get('package').get('persistent_disk', 0),
                        'name': 'persistent_disk',
                        'type': 'integer'},
                        {'configurable': True,
                        'constraints': {'min': job.get('package').get('cpu')},
                        'default': job.get('package').get('cpu'),
                        'name': 'cpu',
                        'type': 'integer'}],
                    'resource_label': job.get('name'),
                    'single_az_only': False,
                    'static_ip': 1,
                    'templates': [
                        {'name': 'containers', 'release': 'docker'},
                        {'name': 'docker', 'release': 'docker'},
                        {'name': job.get('type'), 'release': release.get('name')},
                        {'consumes': 
                            literal_unicode(
                                'nats:\n'
                                '  from: nats\n'
                                '  deployment: (( ..cf.deployment_name ))\n'
                            ),
                            'name': 'route_registrar',
                            'release': 'routing'}
                    ],
                    'property_blueprints': [
                        {
                            'default': {'identity': 'vcap'},
                            'name': 'vm_credentials',
                            'type': 'salted_credentials'},
                        {
                            'name': 'app_credentials',
                            'type': 'salted_credentials'
                        }
                    ],
                    'manifest': {
                        'allow_paid_service_plans': '(( .properties.allow_paid_service_plans.value ))',
                        'app_domains': ['(( ..cf.cloud_controller.apps_domain.value ))'],
                        'apply_open_security_group': '(( .properties.apply_open_security_group.value ))',
                        'cf': {
                            'admin_password': '(( ..cf.uaa.system_services_credentials.password ))',
                            'admin_user': '(( ..cf.uaa.system_services_credentials.identity ))'},
                        'domain': '(( ..cf.cloud_controller.system_domain.value ))',
                        'org': '(( .properties.org.value ))',
                        'security': {
                            'password': '(( .' + job.get('name') + '.app_credentials.password ))',
                            'user': '(( .' + job.get('name') + '.app_credentials.identity ))'},
                        'space': '(( .properties.space.value ))',
                        'ssl': {'skip_cert_verify': '(( ..cf.ha_proxy.skip_cert_verify.value ))'},
                        'tls_cacert': '(( $ops_manager.ca_certificate ))',
                        'tls_cert': '(( .properties.generated_rsa_cert_credentials.cert_pem ))',
                        'tls_key': '(( .properties.generated_rsa_cert_credentials.private_key_pem ))',
                    }
                }

                release_job['manifest'].update(job.get('package', {}).get('manifest', {}))
                release_job_manifest = release_job['manifest']
                
                routes = {'routes': list()}
                for route in job.get('package', {}).get('routes', []):
                    route_name = route.get('prefix') + '-' + job.get('package').get('name').replace('_','-')
                    routes['routes'].append({
                        'name': route_name,
                        'port': route.get('port'),
                        'registration_interval': '20s',
                        'uris': ['%s.(( ..cf.cloud_controller.system_domain.value ))' % route_name]
                    })
                release_job_manifest['route_registrar'] = routes

                for prop in self.config.get('all_properties'):
                    prop = template_helper.render_property(prop)
                    release_job_manifest.update(prop)

                for service_plan_form in self.config.get('service_plan_forms', []):
                    form_name = service_plan_form.get('name')
                    release_job_manifest[form_name] =  '(( .properties.' + form_name + '.value ))'

                for package in self.config.get('packages', []):
                    pkg_name = package.get('name')
                    pkg_manifest = {'name': pkg_name}
                    if package.get('is_external_broker'):
                        pkg_manifest.update({
                            'url': '(( .properties.' + pkg_name + '_url.value ))',
                            'user': '(( .' + pkg_name + '_user.value ))',
                            'password': '(( .' + pkg_name + '_password.value ))',
                        })
                    elif package.get('is_broker'):
                        pkg_manifest.update({
                            'user': '(( .' + job.get('name') + '.app_credentials.identity ))',
                            'password': '(( .' + job.get('name') + '.app_credentials.password ))',
                        })

                    if package.get('is_broker'):
                        pkg_manifest.update({
                            'enable_global_access_to_plans': '(( .properties.' + pkg_name + '_enable_global_access_to_plans.value ))',
                        })

                    if package.get('is_buildpack'):
                        pkg_manifest.update({
                            'buildpack_order': '(( .properties.' + pkg_name + '_buildpack_order.value ))',
                        })

                    release_job_manifest[pkg_name] = pkg_manifest
                release_job['manifest'] = literal_unicode(template_helper.render_yaml(release_job_manifest))

                instance_def = {
                'configurable': True,
                'default': job.get('instances', 1),
                'name': 'instances',
                'type': 'integer'
                }
                if self.config['metadata_version'] < 1.7:
                    release_job['instance_definitions'] = [instance_def]
                else:
                    release_job['instance_definition'] = instance_def

                job_types.append(release_job)

            if release.get('package-type') == 'bosh-release':
                for job in release.get('jobs', []):
                    bosh_release_job = {
                        'name': job.get('name'), 
                        'resource_label': job.get('label') or job.get('name'),
                        'dynamic_ip': job.get('dynamic_ip', 0),
                        'max_in_flight': job.get('max_in_flight', 1),
                        'single_az_only': job.get('single_az_only', True if job.get('lifecycle') == 'errand' else False),
                        'static_ip': job.get('static_ip', 0),
                        'property_blueprints': [{
                            'default': {'identity': 'vcap'},
                            'name': 'vm_credentials',
                            'type': 'salted_credentials'
                        }],
                        'manifest': literal_unicode(template_helper.render_yaml(job.get('manifest'))),
                    }
                    if job.get('lifecycle') == 'errand':
                        bosh_release_job['errand'] = True
                        if job.get('run_post_deploy_errand_default'):
                            bosh_release_job['run_post_deploy_errand_default'] = job.get('run_post_deploy_errand_default')
                        if job.get('run_pre_delete_errand_default'):
                            bosh_release_job['run_pre_delete_errand_default'] = job.get('run_pre_delete_errand_default')

                    bosh_release_job['templates'] = list()
                    for template in job.get('templates'):
                        temp = {
                            'name': template.get('name'), 
                            'release': template.get('release')
                        }
                        if template.get('consumes'):
                            temp['consumes'] = literal_unicode(yaml.dump(template.get('consumes'), default_flow_style=False))
                        if template.get('provides'):
                            temp['provides'] = literal_unicode(yaml.dump(template.get('provides'), default_flow_style=False))
                        bosh_release_job['templates'].append(temp)

                    bosh_release_job['resource_definitions'] = [{
                        "default": job.get('memory', 512), 
                        "configurable": True, 
                        "type": "integer", 
                        "name": "ram", 
                        "constraints": {
                          "min": job.get('memory', 0)
                        }
                      }, 
                      {
                        "default": job.get('ephemeral_disk', 4096), 
                        "configurable": True, 
                        "type": "integer", 
                        "name": "ephemeral_disk", 
                        "constraints": {
                          "min": job.get('ephemeral_disk', 0)
                        }
                      }, 
                      {
                        "default": job.get('persistent_disk', 0), 
                        "configurable": False if job.get('lifecycle') == 'errand' else True, 
                        "type": "integer", 
                        "name": "persistent_disk", 
                        "constraints": {
                          "min": job.get('persistent_disk', 0)
                        }
                      }, 
                      {
                        "default": job.get('cpu', 1), 
                        "configurable": True, 
                        "type": "integer", 
                        "name": "cpu", 
                        "constraints": {
                          "min": job.get('cpu', 1)
                        }
                    }]
                
                    if job.get('default_internet_connected') != None:
                        bosh_release_job['default_internet_connected'] = job.get('default_internet_connected')

                    instance_def = {
                    'configurable': True,
                    'default': job.get('instances', 1),
                    'name': 'instances',
                    'type': 'integer'
                    }
                    if job.get('singleton') or job.get('lifecycle') == 'errand':
                        instance_def['configurable'] = False
                        instance_def['default'] = 1
                    if self.config['metadata_version'] < 1.7:
                        bosh_release_job['instance_definitions'] = [instance_def]
                    else:
                        bosh_release_job['instance_definition'] = instance_def

                    job_types.append(bosh_release_job)

            #
            # {{ job.type }} job
            #
            if not release.get('package-type') == 'bosh-release':
                for job in [j for j in release.get('jobs', []) if not j.get('template') == 'docker-bosh']:
                    if release.get('package-type') == 'kibosh' and job.get('name').startswith('charts_for_'):
                        continue
                    job_type = {
                        'name': job.get('name'),
                        'resource_label': job.get('name'),
                        'errand': True,
                        "templates": [{
                            "release": release.get('name'), 
                            "name": job.get('type'),
                        }],
                        "resource_definitions": [{
                            "default": 1024, 
                            "type": "integer", 
                            "name": "ram", 
                            "configurable": True
                          }, 
                          {
                            "default": 4096, 
                            "type": "integer", 
                            "name": "ephemeral_disk", 
                            "configurable": True
                          }, 
                          {
                            "default": 0, 
                            "configurable": False if job.get('lifecycle') == 'errand' else True, 
                            "type": "integer", 
                            "name": "persistent_disk", 
                            "constraints": {
                              "min": 0
                            }
                          }, 
                          {
                            "default": 1, 
                            "type": "integer", 
                            "name": "cpu", 
                            "configurable": True
                        }],
                        "static_ip": 0, 
                        "dynamic_ip": 1,
                        "max_in_flight": 1, 
                        "single_az_only": True,
                        "property_blueprints": [{
                            "default": {"identity": "vcap"}, 
                            "type": "salted_credentials", 
                            "name": "vm_credentials"
                          }, 
                          {
                            "type": "salted_credentials", 
                            "name": "app_credentials"
                          }
                        ], 
                        "manifest": literal_unicode(template_helper.render_yaml(job.get('manifest')))
                    }
                    if job.get('run_post_deploy_errand_default'):
                        job_type['run_post_deploy_errand_default'] = job.get('run_post_deploy_errand_default')
                    if job.get('run_pre_delete_errand_default'):
                        job_type['run_pre_delete_errand_default'] = job.get('run_pre_delete_errand_default')
                    if release.get('consumes_for_deployment'):
                        job_type['templates'][0]["consumes"] = literal_unicode(yaml.dump(release.get('consumes_for_deployment'), default_flow_style=False))

                    instance_def = {
                    'configurable': False,
                    'default': 1,
                    'name': 'instances',
                    'type': 'integer'
                    }
                    if self.config['metadata_version'] < 1.7:
                        job_type['instance_definitions'] = [instance_def]
                    else:
                        job_type['instance_definition'] = instance_def

                    job_types.append(job_type)

        # Return value
        self.tile_metadata['job_types'] = job_types

    def _build_runtime_config(self):
        # TODO: this should be making a copy not clobbering the original.
        for runtime_conf in self.config.get('runtime_configs', {}):
            if runtime_conf.get('runtime_config'):
                runtime_conf['runtime_config'] = yaml.dump(runtime_conf['runtime_config'], default_flow_style=False)
        self.tile_metadata['runtime_configs'] = self.config.get('runtime_configs')
