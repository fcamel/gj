#!/usr/bin/env python
# -*- encoding: utf8 -*-

import unittest

import gj_util

class GJUtilTest(unittest.TestCase):
    def setUp(self):
        self._input = []

        self._gid = gj_util._gid
        def mockGid(pattern):
            return self.mockGid(pattern)

        gj_util._gid = mockGid

    def tearDown(self):
        gj_util._gid = self._gid

    def mockGid(self, pattern):
        return self._input

    def testFindDeclarationOrDefinitionForCppClass(self):
        self._input = [
            'path/to/a.cpp:123: class MyClass',
            'path/to/a.cpp:456: MyClass tmp;',
        ]

        actual = gj_util.find_declaration_or_definition('MyClass')
        expected = 'path/to/a.cpp:123:7: class MyClass'
        self.assertEquals(1, len(actual))
        self.assertEquals(expected, str(actual[0]))

    def testFindDeclarationOrDefinitionForCppTypedef(self):
        self._input = [
            'path/to/a.cpp:456: MyClass tmp;',
            'path/to/a.cpp:123: typedef MyClass SomeClass',
        ]

        actual = gj_util.find_declaration_or_definition('MyClass')
        expected = 'path/to/a.cpp:123:9: typedef MyClass SomeClass'
        self.assertEquals(1, len(actual))
        self.assertEquals(expected, str(actual[0]))

    def testFindDeclarationOrDefinitionForCppMethod(self):
        self._input = [
            'path/to/a.cpp:456: tmp.MyMethod();',
            'path/to/a.cpp:123: void MyMethod() { /**/ }',
        ]

        actual = gj_util.find_declaration_or_definition('MyMethod')
        expected = 'path/to/a.cpp:123:6: void MyMethod() { /**/ }'
        self.assertEquals(1, len(actual))
        self.assertEquals(expected, str(actual[0]))


if __name__ == '__main__':
    unittest.main()
