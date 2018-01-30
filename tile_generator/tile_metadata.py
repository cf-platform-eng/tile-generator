import yaml


class TileMetadata(object):
    def __init__(self, config):
        self.config = config
        self.tile_metadata = dict()

    def build(self):
        self._build_base()
        self._build_stemcell_criteria()
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
        self.tile_metadata['base'] = base

    def _build_stemcell_criteria(self):
        stemcell_criteria = dict()
        # Note: tile.py uses self.config['stemcell_criteria']
        stemcell_criteria['os'] = self.config['stemcell_criteria']['os']
        stemcell_criteria['requires_cpi'] = False
        stemcell_criteria['version'] = str(self.config.get('stemcell_criteria', {}).get('version', 3312))
        self.tile_metadata['stemcell_criteria'] = {'stemcell_criteria': stemcell_criteria}

    def _build_runtime_config(self):
        # TODO: this should be making a copy not clobbering the original.
        for runtime_conf in self.config.get('runtime_configs', {}):
            if runtime_conf.get('runtime_config'):
                runtime_conf['runtime_config'] = yaml.dump(runtime_conf['runtime_config'], default_flow_style=False)
        self.tile_metadata['runtime_configs'] = self.config.get('runtime_configs')