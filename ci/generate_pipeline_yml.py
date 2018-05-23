#!/usr/bin/env python

from jinja2 import Template

clusters = ['1-11', '1-12', '2-0', '2-1', '2-2', 'multi-az']

with open('pipeline.yml.jinja2', 'r') as f:
  t = Template(f.read());

with open('pipeline.yml', 'w') as f:
  f.write(t.render(clusters=clusters))

print "Successfully generated pipeline.yml"
