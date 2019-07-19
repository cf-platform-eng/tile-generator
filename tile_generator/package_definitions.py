import copy
import os
import sys
import yaml

from . import package_flags as flag

# Inspired by https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
def merge_dict(dct, merge_dct):
    for k, v in merge_dct.items():
        if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict):
            merge_dict(dct[k], merge_dct[k])
        else:
            dct[k] = copy.deepcopy(merge_dct[k])

# This coerce belongs to PackageDockerBosh, but needs
# to be reachable by BasePackage
def _to_yaml(manifest):
    try:
        return yaml.safe_load(manifest)
    except:
        print('docker-bosh manifest must be valid yaml')
        sys.exit(1)


class BasePackage(object):
    _schema = {
        # NOTE: Is the '-' to '_' conversion really needed?
        'name': {'type': 'string', 'required': True, 'regex': '[a-z][a-z0-9]*(_[a-z0-9]+)*$','coerce': lambda v: v.lower().replace('-','_')},
    }

    @classmethod
    def schema(self):
        # Start by defining the package-type of the child most class
        schema = {'package-type': {'type': 'string', 'required': True, 'allowed': [self.package_type]}}
        for s in self.__mro__[::-1]:
            try:
                merge_dict(schema, s._schema)
            except AttributeError:
                pass
        return schema

    @classmethod
    def normalize_file_lists(self, package):
        files = package.get('files', [])
        path = package.get('path')
        if path is not None:
            files += [ { 'path': path } ]
            package['path'] = os.path.basename(path)
        manifest = package.get('manifest', {})
        manifest_path = manifest.get('path', None)
        if manifest_path is not None:
            files += [ { 'path': manifest_path } ]
            package['manifest']['path'] = os.path.basename(manifest_path)
        for docker_image in package.get('docker_images', []):
            filename = docker_image.lower().replace('/','-').replace(':','-') + '.tgz'
            files += [ { 'path': 'docker:' + docker_image, 'name': filename } ]
        for file in files:
            file['name'] = file.get('name', os.path.basename(file['path']))

        package['files'] = files


class PackageBoshRelease(BasePackage):
    package_type = 'bosh-release'
    flags = [flag.BoshRelease]
    _schema = {
        'jobs': {'type': 'list', 'required': False, 'schema':{
            'type': 'dict', 'schema': {
                'name': {'type': 'string', 'required': True, 'regex': '^[a-zA-Z0-9\-\_]*$'},
                'memory': {'required': False, 'type': 'number'},
                'varname': {'type': 'string', 'default_setter': lambda doc: doc['name'].lower().replace('-','_')}
            }
        }},
    }

    @classmethod
    def normalize_file_lists(self, package):
        pass


class PackageDockerBosh(BasePackage):
    package_type = 'docker-bosh'
    flags = [flag.DockerBosh] # flag.Docker
    _schema = {
        # TODO: Remove the dependency on this in templates
        'is_docker': {'type': 'boolean', 'default': True},
        'docker_images': {'required': False},
        'memory': {'required': False, 'type': 'number'},
        'routes': {'required': False, 'type': 'list', 'schema': {'type': 'dict', 'schema': {
            'prefix': {'required': True},
            'port': {'required': True},}}},
        'manifest': {'type': 'dict', 'allow_unknown': True, 'required': True, 'coerce': _to_yaml,
                     'keyschema': {'forbidden': ['path']}, 'schema': {
            'containers': {'type': 'list', 'schema': {'type': 'dict', 'schema': {
                'name': {'type': 'string', 'required': True, 'regex': '^[a-z][a-zA-Z0-9_]*$'},
                'env_file': {'type': 'list', 'default': [], 'schema': {
                    'type': 'string'}}}}}}},
    }


class BaseAppAndAppBroker(BasePackage):
    flags = [flag.Cf, flag.App]
    _schema = {
        'manifest': {'type': 'dict', 'allow_unknown': True, 'required': True,
                     'keyschema': {'forbidden': ['random-route']},
                     'schema': {'buildpack': {'required': True}}},
    }


class PackageApp(BaseAppAndAppBroker):
    package_type = 'app'
    flags = BaseAppAndAppBroker.flags


class PackageAppBroker(BaseAppAndAppBroker):
    package_type = 'app-broker'
    flags = BaseAppAndAppBroker.flags + [flag.Broker] # flag.BrokerApp


class PackageBuildpack(BasePackage):
    package_type = 'buildpack'
    flags = [flag.Cf, flag.Buildpack]


class PackageDecorator(BasePackage):
    package_type = 'decorator'
    flags = [flag.Cf, flag.Buildpack, flag.Decorator]


class PackageExternalBroker(BasePackage):
    package_type = 'external-broker'
    flags = [flag.Cf, flag.Broker, flag.ExternalBroker]


class PackageDockerApp(BasePackage):
    package_type = 'docker-app'
    flags = [flag.Cf, flag.App] # flag.Docker, flag.DockerApp
    _schema = {
        # TODO: Remove the dependency on this in templates
        'is_docker': {'type': 'boolean', 'default': True},
        'is_docker_app': {'type': 'boolean', 'default': True},
        'manifest': {'type': 'dict', 'allow_unknown': True, 'required': True,
                     'keyschema': {'forbidden': ['path']}, 'schema': {}},
    }


class PackageDockerAppBroker(BasePackage):
    package_type = 'docker-app-broker'
    flags = [flag.Cf, flag.App, flag.Broker] # flag.Docker flag.BrokerApp, flag.DockerApp,
    _schema = {
        # TODO: Remove the dependency on this in templates
        'is_docker': {'type': 'boolean', 'default': True},
        'is_docker_app': {'type': 'boolean', 'default': True},
        'manifest': {'type': 'dict', 'allow_unknown': True, 'required': True,
                     'keyschema': {'forbidden': ['path']}, 'schema': {}},
    }


class PackageBlob(BasePackage):
    package_type = 'blob'
    flags = [flag.Cf] # flag.Blob


class PackageHelm(BasePackage):
    package_type = 'helm'
    flags = [flag.Helm]
    _schema = {
        'path': {'type': 'string', 'required': True },
        'zip_if_needed': {'type': 'boolean', 'default': True}
    }