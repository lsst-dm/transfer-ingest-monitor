#!/usr/bin/env python

import base64
import os
import sys
from jinja2 import Template
import yaml

def render_template(name, files):
    with open(os.path.join(os.path.dirname(__file__), "secret.tpl.yaml")) as f:
        templateText = f.read()
    template = Template(templateText)
    secret_yaml = yaml.safe_load(template.render(
        name=name,
        files=files,
    ))
    return yaml.dump(secret_yaml, indent=2)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Convert a list of files into a Kubernetes Secret.')
    parser.add_argument('--name', nargs='?', default='my-secret', help='name of secret')
    parser.add_argument('--output', nargs='?', help='output file', type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('files', metavar='file', type=str, nargs='+',
                        help='a file to add to the secret')
    args = parser.parse_args()
    
    # out_file = os.path.join(os.path.dirname(__file__), args.output)
    
    secret_files = []
    for file in args.files:
        if os.path.isfile(file):
            # print(f'Adding file "{file}"...')
            try:
                with open(file, 'r') as secret_file:
                    data = secret_file.read()
                    data_b64 = base64.encodebytes(bytes(data, 'utf-8')).decode('utf-8').replace('\n', '')
                    # print(data_b64)
                    secret_files.append({
                        'name': os.path.basename(file),
                        'data': data_b64,
                    })
            except Exception as e:
                print(f'Error converting file "{file}": {str(e)}')
        else:
            print(f'File "{file}" does not exist. Skipping...')
    # print('Generating secret...')
    secret_yaml = render_template(args.name, secret_files)
    # print(f'{yaml.dump(secret_yaml, indent=2)}')
    
    # with open(outfilepath, 'w') as out_file:
        # out_file.write(secret_yaml)
    args.output.write(f'{secret_yaml}')
        
if __name__ == "__main__":
    main()