'''
When compiling with -ftime-trace clang (and gcc) will create a small json file containing timing information.
This script find those .json files and aggregate the results.
'''

import argparse
import os
import json
import collections
import sys
import shutil


def walk_source_files(dn: str, filters):
    paths = []

    for root, _, files in os.walk(dn):
        for path in files:
            if path.endswith('.cpp.json') or path.endswith('.c.json') or path.endswith('.cc.json'):
                abspath = os.path.join(root, path)

                skip = False
                if filters is not None:
                    for filt in filters:
                        if filt in path:
                            filt = True

                if not skip:
                    paths.append(abspath)

    return paths


def find_includes(path):
    includes = {}

    with open(path) as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            return {}

        try:
            data = json.loads(content)
        except:
            return {}

    # breakpoint()
    if 'beginningOfTime' not in content:
        return {}

    for e in data.get('traceEvents', []):
        path = e.get('args', {}).get('detail')
        duration = e.get('dur')
        name = e.get('name')

        if path is not None and duration is not None and name == 'Source':
            includes[path] = duration

    return includes


def progress_bar(current, total, width=40):
    progress = current / total
    filled = int(width * progress)
    bar = '#' * filled + '-' * (width - filled)
    sys.stderr.write(f'\r[{bar}] {progress:.0%}')
    sys.stderr.flush()


def run(args):
    includes_weight = collections.defaultdict(int)

    cols, _ = shutil.get_terminal_size(fallback=(80, 24))
    cols -= 7

    files = walk_source_files(args.root, args.filters)
    print(f'Found {len(files)} json files in {args.root}')

    for i, path in enumerate(files):
        progress_bar(i, len(files), cols)

        includes = find_includes(path)
        for include, cost in includes.items():
            includes_weight[include] += cost

    scores = []
    for path, duration in includes_weight.items():
        scores.append((duration, path))

    scores.sort()
    for count, filename in scores:
        print(filename, count)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root folder to explore")
    parser.add_argument("--filters", "-F", help="Source files to filter out when scanning", action='append')
    
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print('Invalid input folder: ', args.root)
        sys.exit(1)

    run(args)
