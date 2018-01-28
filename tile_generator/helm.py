import os
import sys
import yaml
import json

def find_required_images(values):
    images = []
    for key, value in values.items():
        if key == 'image':
            if isinstance(value, dict):
                image = value.get('repository')
                tag = value.get('tag', None)
            else:
                image = value
                tag = values.get('imageTag', None)
            if tag is not None:
                image += ':' + tag
            images += [ image ]
        else:
            if isinstance(value, dict):
                images += find_required_images(value)
    return images

def get_chart_info(chart_dir):
    chart_file = os.path.join(chart_dir, 'Chart.yaml')
    with open(chart_file) as f:
        chart = yaml.safe_load(f)
    values_file = os.path.join(chart_dir, 'values.yaml')
    with open(values_file) as f:
        chart_values = yaml.safe_load(f)

    return {
        'name': chart['name'],
        'version': chart['version'],
        'required_images': find_required_images(chart_values),
    }

if __name__ == '__main__':
    for chart in sys.argv[1:]:
        print(json.dumps(get_chart_info(chart), indent=4))
