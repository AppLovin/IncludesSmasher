import unittest
import tempfile
import os
import shutil

from includes_patcher import patch_file
from includes_smasher import find_includes, find_descendants


class TestIncludesPatcher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_patch_file_with_existing_includes(self):
        file_path = os.path.join(self.test_dir, 'sample.cpp')
        with open(file_path, 'w') as f:
            f.write('#include <iostream>\n#include <string>\n\nint main() {}\n')

        patch_file(file_path, 'vector')

        with open(file_path) as f:
            content = f.read()

        expected = '#include <iostream>\n#include <string>\n#include "vector"\n\nint main() {}\n'
        self.assertEqual(content, expected)

    def test_patch_file_with_bracket_include(self):
        file_path = os.path.join(self.test_dir, 'sample2.cpp')
        with open(file_path, 'w') as f:
            f.write('#include <iostream>\n\nint main() {}\n')

        patch_file(file_path, '<vector>')

        with open(file_path) as f:
            content = f.read()

        expected = '#include <iostream>\n#include <vector>\n\nint main() {}\n'
        self.assertEqual(content, expected)

    def test_patch_file_with_no_includes(self):
        file_path = os.path.join(self.test_dir, 'sample_no_inc.cpp')
        with open(file_path, 'w') as f:
            f.write('#pragma once\n\nclass Foo {};\n')

        patch_file(file_path, 'foo.h')

        with open(file_path) as f:
            content = f.read()

        expected = '#pragma once\n#include "foo.h"\n\nclass Foo {};\n'
        self.assertEqual(content, expected)

    def test_patch_empty_file(self):
        file_path = os.path.join(self.test_dir, 'empty.cpp')
        with open(file_path, 'w') as f:
            f.write('')

        patch_file(file_path, 'foo.h')

        with open(file_path) as f:
            content = f.read()

        expected = '#include "foo.h"\n'
        self.assertEqual(content, expected)

    def test_skip_already_included(self):
        file_path = os.path.join(self.test_dir, 'dup.cpp')
        with open(file_path, 'w') as f:
            f.write('#include "foo.h"\n')

        patch_file(file_path, 'foo.h')

        with open(file_path) as f:
            content = f.read()

        expected = '#include "foo.h"\n'
        self.assertEqual(content, expected)


class TestIncludesSmasher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_includes(self):
        file_path = os.path.join(self.test_dir, 'test.cpp')
        with open(file_path, 'w') as f:
            f.write('''
#include <vector>
#include "my_header.h"
#  include <map>
// #include <commented.h>
/* #include <block_comment.h> */
// Here we discuss #include <fake.h>
std::string s = "#include <literal.h>";
''')

        includes = find_includes(file_path)
        self.assertEqual(includes, ['vector', 'my_header.h', 'map'])

    def test_find_descendants(self):
        includes = {
            'a.h': ['b.h', 'c.h'],
            'b.h': ['d.h'],
            'c.h': ['d.h'],
            'd.h': [],
        }
        descendants = find_descendants('a.h', includes)
        self.assertIn('b.h', descendants)
        self.assertIn('c.h', descendants)
        self.assertIn('d.h', descendants)


if __name__ == '__main__':
    unittest.main()
