#!/usr/bin/env python3
# -*- encoding: utf8 -*-

import unittest
import gj_index

class TestGetSymbol(unittest.TestCase):
    def test_get_symbol(self):
        data = 'A B::C(D::E)'
        expected = 'C'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

        data = 'A B::C()'
        expected = 'C'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

        data = 'A B::C'
        expected = 'C'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

    def test_get_symbol_with_multiple_parenthesis(self):
        # The class and its methods are defined in a method.
        data = 'A::B()::C::D()'
        expected = 'D'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

    def test_get_symbol_with_operator(self):
        data = 'A::B::operator()()'
        expected = 'operator()'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

    def test_get_symbol_with_template(self):
        data = 'A::B<C::D>()'
        expected = 'B'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

    def test_get_symbol_with_nested_template(self):
        data = 'A<X::Y>::B<C::D<E::F> >()'
        expected = 'B'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)

    def test_get_symbol_with_nested_parenthesis(self):
        data = '''A<(anonymous namespace)::B>::C((anonymous namespace)::D*)'''
        expected = 'C'
        actual = gj_index._get_symbol(data)
        self.assertEqual(expected, actual)



if __name__ == '__main__':
    unittest.main()
