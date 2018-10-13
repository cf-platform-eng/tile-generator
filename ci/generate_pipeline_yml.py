#!/usr/bin/env python

import os
from jinja2 import Template

clusters = ['2_0', '2_1', '2_2']
# Commenting out this as we only have one example and it breaks
tiles = [] # [d for d in os.listdir('../examples') if os.path.isdir(os.path.join('../examples', d))]

with open('pipeline.yml.jinja2', 'r') as f:
  t = Template(f.read());

with open('pipeline.yml', 'w') as f:
  f.write(t.render(clusters=clusters, tiles=tiles))

print "Successfully generated pipeline.yml"
