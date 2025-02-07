#!/usr/bin/python3
# Update Antora attributes for OS and tool versions.

import os
import requests
import sys
import base64
import yaml

GITHUB_RELEASES = {
    'butane-version': 'coreos/butane',
    'butane-latest-stable-spec': 'coreos/butane',
    'ignition-version': 'coreos/ignition',
}
FCOS_STREAMS = {
    'stable-version': 'stable',
}

basedir = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
github_token = os.getenv('GITHUB_TOKEN')

with open(os.path.join(basedir, 'antora.yml'), 'r+') as fh:
    config = yaml.safe_load(fh)
    attrs = config.setdefault('asciidoc', {}).setdefault('attributes', {})
    orig_attrs = attrs.copy()

    for attr, repo in GITHUB_RELEASES.items():
        headers = {'Authorization': f'Bearer {github_token}'} if github_token else {}
        if attr == 'butane-version' or attr == 'ignition-version':
            resp = requests.get(
                f'https://api.github.com/repos/{repo}/releases/latest',
                headers=headers
            )
            resp.raise_for_status()
            tag = resp.json()['tag_name']
            attrs[attr] = tag.lstrip('v')
        elif attr == 'butane-latest-stable-spec':
            resp = requests.get(
                f'https://api.github.com/repos/{repo}/contents/docs/specs.md',
                headers=headers
            )
            resp.raise_for_status()
            attrs[attr] = ''.join(str(base64.b64decode(resp.json()['content'])).split('- ', 3)[2:3])[2:-26]

    for attr, stream in FCOS_STREAMS.items():
        resp = requests.get(f'https://builds.coreos.fedoraproject.org/streams/{stream}.json')
        resp.raise_for_status()
        # to be rigorous, we should have a separate attribute for each
        # artifact type, but the website doesn't do that either
        attrs[attr] = resp.json()['architectures']['x86_64']['artifacts']['metal']['release']

    if attrs != orig_attrs:
        fh.seek(0)
        fh.truncate()
        fh.write("# Automatically modified by update-versions.py; comments will not be preserved\n\n")
        yaml.safe_dump(config, fh, sort_keys=False)
