#!/usr/bin/env python
# -*- encoding: utf8 -*-

import sys
import optparse

import gj_util


__author__ = 'fcamel'


def main():
    '''\
    %prog [options] <pattern> [<pattern> ...]
    '''
    parser = optparse.OptionParser(usage=main.__doc__)
    parser.add_option('-d', '--declaration', dest='declaration', action='store_true', default=False,
                      help='Find possible declarations.')
    options, args = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        return 1

    if options.declaration:
        matches = gj_util.find_declaration_or_definition(args[0])
    else:
        matches = gj_util.get_list(args)
    for m in matches:
        print unicode(m).encode('utf8')

    return 0


if __name__ == '__main__':
    sys.exit(main())
