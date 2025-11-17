'''
Given a list of files to patch, and add header automatically.

This is done by finding the last #include line in a file and append a new include after that.

It is convenient to combine this script with a search script like grep (we prefer ag which is faster).

$ ./includes_patcher.py --include my_header.h `ag -l 'getFoo\(\)' ../`

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


def patch_file(path, new_include):
    '''
    Search for the last #include
    '''
    j = 0
    with open(path) as f:
        content = f.read()
        lines = content.splitlines()

    if new_include in content:
        return

    for i, line in enumerate(lines):
        if '#include' in line:
            j = i

    top_lines = lines[0:j+1]
    new_include_line = [f'#include "{new_include}"']
    bottom_lines = lines[j+1:]

    end_of_file_is_new_line = content[-1] == '\n'

    with open(path, 'w') as f:
        new_lines = top_lines + new_include_line + bottom_lines
        new_content = '\n'.join(new_lines)
        end_char = '\n' if end_of_file_is_new_line else ''
        f.write(new_content + end_char)
        

def patch_all_files(args):
    for path in args.files:
        patch_file(path, args.include)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help="Files to patch", nargs='+')
    parser.add_argument("--include", help="include to add")
    args = parser.parse_args()

    patch_all_files(args)
