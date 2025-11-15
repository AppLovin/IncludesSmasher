#!/usr/bin/env python3
'''
To sort by the file whose include complexity is the highest

./includes_smasher.py -r path/to/folder | sort -k 2 -n
'''

import sys
import os
import collections
import argparse
from typing import Dict, List


def walk_source_files(dn: str):
    paths = []

    for root, _, files in os.walk(dn):
        for path in files:
            _, ext = os.path.splitext(path)
            if ext not in ('.c', '.cpp', '.h', '.hpp'):
                continue

            abspath = os.path.join(root, path)
            paths.append(abspath)

    return paths


def find_includes(path: str) -> list[str]:
    includes = []

    try:
        with open(path) as f:
            content = f.read()
    except:
        return []

    lines = content.splitlines()
    for line in lines:
        if '#include' in line:
            tokens = line.split()
            if len(tokens) > 1:
                filename = tokens[1]
                filename = filename.replace('"', '').replace("'", '')
                filename = filename.replace('<', '').replace('>', '')

                if filename != '#include':
                    includes.append(filename)

    return includes


# Thank you ChatGPT
def find_descendants(filename: str, includes: Dict[str, Iterable[str]]) -> List[str]:
    """
    Iterative DFS using an explicit stack.
    - Appends every encountered include (duplicates allowed).
    - Avoids infinite recursion by guarding cycles *per current path* (not globally).
    """
    result: List[str] = []

    # Stack holds (current_node, iterator over its children, path_set)
    stack: List[Tuple[str, Iterable[str], Set[str]]] = []

    # Start at the root filename
    root_children = list(includes.get(filename, []))
    stack.append((filename, iter(root_children), {filename}))

    while stack:
        node, it, path = stack[-1]
        try:
            child = next(it)
            result.append(child)  # record every include edge (even if repeated via other paths)

            # If child is not on the *current* path, descend
            if child not in path:
                child_children = list(includes.get(child, []))
                # push new frame with updated path
                stack.append((child, iter(child_children), path | {child}))
            # else: cycle detected on this path—do not descend, but we already counted the include
        except StopIteration:
            # done with this node
            stack.pop()

    return result


def build_include_mapping(src_root, include_paths):
    includes = collections.defaultdict(list)

    paths = walk_source_files(src_root)

    # First path collect all header -> [header1, header2, ...] relationships
    for path in paths:
        path_filename = os.path.basename(path)
        path_includes = find_includes(path)
        _, ext = os.path.splitext(path)

        for include in path_includes:
            filename = os.path.basename(include)

            # trim includes
            if ext in ('.h', '.hpp'):
                includes[path_filename].append(filename)

    # Now look for headers
    if include_paths is not None:
        for include_path in include_paths:
            paths = walk_source_files(include_path)

            for path in paths:
                path_filename = os.path.basename(path)
                _, ext = os.path.splitext(path)

                if ext not in ('.h', '.hpp'):
                    continue

                path_includes = find_includes(path)

                for include in path_includes:
                    filename = os.path.basename(include)

                    includes[path_filename].append(filename)

    return includes


def run(src_root, include_paths):
    includes = build_include_mapping(src_root, include_paths)

    total_deps = 0

    includes_descendants = {}
    includes_counter = collections.defaultdict(int)

    paths = walk_source_files(src_root)

    scores = []

    for path in paths:
        _, ext = os.path.splitext(path)
        if ext not in ('.c', '.cpp'):
            continue

        deps_count = 0
        path_includes = find_includes(path)

        all_descendants = []
        for include in path_includes:
            filename = os.path.basename(include)

            descendants = includes_descendants.get(filename)
            if descendants is None:
                descendants = find_descendants(filename, includes)

                includes_descendants[filename] = descendants

            deps_count += len(descendants)

            for descendant in descendants:
                all_descendants.append(descendant)
                includes_counter[descendant] += 1

        scores.append((deps_count, path))
        total_deps += deps_count

        if args.save and os.path.basename(path) == args.filename:
            with open('/tmp/deps', 'w') as f:
                f.write('\n'.join(all_descendants))

        if args.verbose:
            for header in all_descendants:
                print('\t' + header)

    scores.sort()
    for score in scores:
        if not args.quiet:
            print(score[1], score[0])

    print('src files total deps', total_deps)

    if args.headers:

        scores = []
        for k, v in includes_counter.items():
            if args.system:
                scores.append((v, k))
            else:
                if k != k.lower(): # lame test to ignore system headers, who are lowercase ...
                    scores.append((v, k))

        scores.sort()
        for count, filename in scores:
            if not args.quiet:
                print(f"{filename:40} {count}")

        print('headers files total deps', sum(score[0] for score in scores))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Root folder to explore")
    parser.add_argument("--include_paths", "-I", help="Headers root folder(s) to explore", action='append')
    parser.add_argument("--filename", help=".cpp file to filter", default='foo.cpp')
    parser.add_argument("--save", help="Save deps for a given file to disk", action='store_true')
    parser.add_argument("--verbose", "-v", help="Print deps for each files", action='store_true')
    parser.add_argument("--headers", help="Display headers deps", action='store_true')
    parser.add_argument("--system", help="Display system headers", action='store_true')
    parser.add_argument("--quiet", help="Only print scores", action='store_true')
    
    args = parser.parse_args()

    run(args.root, args.include_paths)
