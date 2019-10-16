#!/usr/bin/env python3
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

    def testFindDeclarationOrDefinitionForGoFunction(self):
        self._input = [
            'path/to/a.go:456: foo();',
            'path/to/a.go:123: func foo() {',
            'path/to/a.go:123: func bar(foo int) {',
            'path/to/b.go:123: func foo() {/**/}',
            'path/to/c.go:123: func foo(a int,',
        ]

        actual = gj_util.find_declaration_or_definition('foo')
        self.assertEquals(3, len(actual))
        expected = 'path/to/a.go:123:6: func foo() {'
        self.assertEquals(expected, str(actual[0]))
        expected = 'path/to/b.go:123:6: func foo() {/**/}'
        self.assertEquals(expected, str(actual[1]))
        expected = 'path/to/c.go:123:6: func foo(a int,'
        self.assertEquals(expected, str(actual[2]))

    def testFindDeclarationOrDefinitionForGoMethod(self):
        self._input = [
            'path/to/a.go:456: foo();',
            'path/to/a.go:123: func (t *MyStruct) foo() {',
            'path/to/a.go:123: func bar(foo int) {',
        ]

        actual = gj_util.find_declaration_or_definition('foo')
        expected = 'path/to/a.go:123:20: func (t *MyStruct) foo() {'
        self.assertEquals(1, len(actual))
        self.assertEquals(expected, str(actual[0]))

        actual = gj_util.find_declaration_or_definition('MyStruct')
        expected = 'path/to/a.go:123:10: func (t *MyStruct) foo() {'
        self.assertEquals(1, len(actual))
        self.assertEquals(expected, str(actual[0]))

    def testFindDeclarationOrDefinitionForGoStruct(self):
        self._input = [
            'path/to/a.go:123:  foo struct {',
            'path/to/a.go:456:  var f foo',
            'path/to/a.go:789:  f = new(foo)',
        ]

        actual = gj_util.find_declaration_or_definition('foo')
        self.assertEquals(1, len(actual))
        expected = 'path/to/a.go:123:2:  foo struct {'
        self.assertEquals(expected, str(actual[0]))


        actual = gj_util.find_declaration_or_definition('f')
        self.assertEquals(1, len(actual))
        expected = 'path/to/a.go:456:6:  var f foo'
        self.assertEquals(expected, str(actual[0]))


if __name__ == '__main__':
    unittest.main()
