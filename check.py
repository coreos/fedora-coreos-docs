#!/usr/bin/python3
#
# Find all FCCs in the doc tree, use the podman FCCT container to run them
# through fcct --strict, and fail on any errors.
#
# An FCC looks like this:
#
# [source,yaml]
# ----
# variant:[...]
# ----
#
# If variant: is missing, we print a warning but continue, since there
# might be non-FCC [source,yaml] documents.

import argparse
import os
import re
import subprocess
import sys
import textwrap

container = os.getenv('FCCT_CONTAINER', 'quay.io/coreos/fcct:release')
matcher = re.compile(r'^\[source,\s*yaml\]\n----\n(.+?\n)----$',
        re.MULTILINE | re.DOTALL)

parser = argparse.ArgumentParser(description='Run validations on docs.')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='log all detected FCCs')
args = parser.parse_args()

def handle_error(e):
    raise e

ret = 0
for dirpath, _, filenames in os.walk('.', onerror=handle_error):
    for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        if not filename.endswith('.adoc'):
            continue
        with open(filepath) as fh:
            filedata = fh.read()
        # Iterate over YAML source blocks
        for match in matcher.finditer(filedata):
            fcc = match.group(1)
            fccline = filedata.count('\n', 0, match.start(1)) + 1
            if not fcc.startswith('variant:'):
                print(f'Ignoring non-FCC at {filepath}:{fccline}')
                continue
            if args.verbose:
                print(f'Checking FCC at {filepath}:{fccline}')
            result = subprocess.run(
                    ['podman', 'run', '--rm', '-i', container, '--strict'],
                    universal_newlines=True, # can be spelled "text" on >= 3.7
                    input=fcc,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE)
            if result.returncode != 0:
                formatted = textwrap.indent(result.stderr.strip(), '  ')
                print(f'Invalid FCC at {filepath}:{fccline}:\n{formatted}')
                ret = 1
sys.exit(ret)
