#!/usr/bin/env python

import dictdiffer
import sys
import yaml


if len(sys.argv) != 3:
    print(('Usage: %s FILE_A FILE_B\nSort tile metadata yaml files and compare FILE_A to FILE_B.' % sys.argv[0].split('/')[-1]))
    sys.exit(1)

with open(sys.argv[1], 'r') as f:
    a = f.read()
with open(sys.argv[2], 'r') as f:
    b = f.read()

aa = yaml.load(a)
bb = yaml.load(b)

for conf in [aa, bb]:
    for release in conf['releases']:
       if release.get('name') == 'test-tile':
           release.pop('version')
           release.pop('file')
    conf.pop('product_version')
    conf.pop('provides_product_versions')
    conf['property_blueprints'] = sorted(conf['property_blueprints'], key=lambda k: k['name'])
    conf['job_types'] = sorted(conf['job_types'], key=lambda k: k['name'])
    for x in conf['job_types']: x['manifest'] = sorted(x['manifest'].items()) if type(x['manifest']) is dict else sorted(yaml.load(x['manifest']).items())

from pprint import pprint
for x in list(dictdiffer.diff(aa,bb)): pprint(x); print('')

