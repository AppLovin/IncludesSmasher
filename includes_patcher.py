#!/usr/bin/env python3
'''
Given a list of files to patch, and add header automatically.

This is done by finding the last #include line in a file and append a new include after that.

It is convenient to combine this script with a search script like grep (we prefer ag which is faster).

$ ./includes_patcher.py --include my_header.h `ag -l 'getFoo' ../`

Here is a typical header.

$ cat my_header.h
#pragma once

class Foo;

class Bar()
{
public:
    Bar() {}

    auto getFoo() -> Foo*
    {
        return mFoo.get();
    }

private:
    std::unique_ptr<Foo> mFoo;
'''

import argparse
import re


def patch_file(path, new_include):
    '''
    Search for the last #include and append after it.
    If no #include is found, append after #pragma once if present, or at top of file.
    '''
    with open(path) as f:
        content = f.read()
        lines = content.splitlines()

    if (new_include.startswith('<') and new_include.endswith('>')) or (
        new_include.startswith('"') and new_include.endswith('"')
    ):
        formatted_include = f'#include {new_include}'
    else:
        formatted_include = f'#include "{new_include}"'

    if formatted_include in content or new_include in content:
        print('Skipping ', path)
        return

    last_include_idx = -1
    pragma_once_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#pragma once'):
            pragma_once_idx = i
        elif re.match(r'^\s*#\s*include\b', line):
            last_include_idx = i

    if last_include_idx != -1:
        insert_idx = last_include_idx + 1
    elif pragma_once_idx != -1:
        insert_idx = pragma_once_idx + 1
    else:
        insert_idx = 0

    top_lines = lines[:insert_idx]
    new_include_line = [formatted_include]
    bottom_lines = lines[insert_idx:]

    end_of_file_is_new_line = content.endswith('\n') if content else True

    with open(path, 'w') as f:
        new_lines = top_lines + new_include_line + bottom_lines
        new_content = '\n'.join(new_lines)
        end_char = '\n' if end_of_file_is_new_line else ''
        f.write(new_content + end_char)

    print('Patched ', path)


def patch_all_files(args):
    for path in args.files:
        patch_file(path, args.include)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help="Files to patch", nargs='+')
    parser.add_argument("--include", required=True, help="include to add")
    args = parser.parse_args()

    patch_all_files(args)

