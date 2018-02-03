import os
import sys
import yaml
import json

def find_required_images(values):
    images = []
    values = { k.lower():v for k,v in values.items() }
    for key, value in values.items():
        if key in [ 'image', 'repository' ]:
            if isinstance(value, dict):
                image = value.get('repository', value.get('name'))
                tag = value.get('tag', value.get('imagetag', None))
                if image is None:
                    images += find_required_images(value)
                    continue
            else:
                image = value
                tag = values.get('tag', values.get('imagetag', None))
            if tag is not None:
                image += ':' + str(tag)
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
        'name': chart.get('name', chart.get('Name')),
        'version': chart.get('version', chart.get('Version')),
        'required_images': find_required_images(chart_values),
    }

if __name__ == '__main__':
    for chart in sys.argv[1:]:
        print(json.dumps(get_chart_info(chart), indent=4))
