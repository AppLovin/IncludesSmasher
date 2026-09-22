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

    # .cxx.json is what CMake's unity build feature emits (CMAKE_UNITY_BUILD),
    # in addition to the more common .cpp.json / .c.json / .cc.json from a
    # normal per-file build.
    extensions = ('.cpp.json', '.c.json', '.cc.json', '.cxx.json')

    for root, _, files in os.walk(dn):
        for path in files:
            if not path.endswith(extensions):
                continue

            abspath = os.path.join(root, path)

            skip = False
            if filters is not None:
                for filt in filters:
                    if filt in path:
                        skip = True

            if not skip:
                paths.append(abspath)

    return paths


def find_includes(path):
    '''
    Sum up the wall time clang spent inside each file's 'Source' trace event.

    Older clang emits a single "complete" event per file (ph == 'X') with the
    duration directly on it ('dur'). Newer clang (LLVM 18+) instead emits a
    pair of "begin"/"end" events (ph == 'b' / 'e') sharing an id, which have
    to be matched up (as a stack, keyed by pid/tid, since 'id' is reused) to
    compute the duration ourselves. Both formats are supported here so this
    script keeps working across clang versions.
    '''
    includes = collections.defaultdict(int)

    with open(path) as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            return {}

        try:
            data = json.loads(content)
        except:
            return {}

    if 'beginningOfTime' not in content:
        return {}

    # Stack of (start_ts, detail) per (pid, tid), for the begin/end format.
    open_spans = collections.defaultdict(list)

    for e in data.get('traceEvents', []):
        if e.get('name') != 'Source':
            continue

        ph = e.get('ph')

        if ph == 'X':
            detail = e.get('args', {}).get('detail')
            duration = e.get('dur')
            if detail is not None and duration is not None:
                includes[detail] += duration

        elif ph == 'b':
            detail = e.get('args', {}).get('detail')
            key = (e.get('pid'), e.get('tid'))
            open_spans[key].append((e.get('ts'), detail))

        elif ph == 'e':
            key = (e.get('pid'), e.get('tid'))
            if not open_spans[key]:
                continue
            start_ts, detail = open_spans[key].pop()
            if detail is None or start_ts is None or e.get('ts') is None:
                continue
            includes[detail] += e.get('ts') - start_ts

    return includes


def progress_bar(current, total, width=40):
    progress = current / total
    filled = int(width * progress)
    bar = '#' * filled + '-' * (width - filled)
    sys.stderr.write(f'\r[{bar}] {progress:.0%}')
    sys.stderr.flush()


def run(args):
    includes_weight = collections.defaultdict(int)
    includes_seen = collections.defaultdict(int)

    cols, _ = shutil.get_terminal_size(fallback=(80, 24))
    cols -= 7

    files = walk_source_files(args.root, args.filters)
    print(f'Found {len(files)} json files in {args.root}')

    for i, path in enumerate(files):
        progress_bar(i, len(files), cols)

        includes = find_includes(path)
        for include, cost in includes.items():
            includes_weight[include] += cost
            includes_seen[include] += 1
    sys.stderr.write('\n')

    scores = []
    for path, duration in includes_weight.items():
        scores.append((duration, path))

    scores.sort()
    for duration, filename in scores:
        print(f'{duration / 1000.0:12.1f}ms  seen={includes_seen[filename]:4d}  {filename}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root folder to explore")
    parser.add_argument("--filters", "-F", help="Source files to filter out when scanning", action='append')
    
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print('Invalid input folder: ', args.root)
        sys.exit(1)

    run(args)
