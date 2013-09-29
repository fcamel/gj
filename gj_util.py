#!/usr/bin/env python
# -*- encoding: utf8 -*-

import os
import platform
import re
import subprocess
import sys


__author__ = 'fcamel'

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

# Input mappings
A_KEEP_STATEMENT  = ';'
A_CLEAN_STATEMENT = '!;'
A_FOLD            = '.'
A_RESTART         = '~'

#-----------------------------------------------------------
# public
#-----------------------------------------------------------
class Match(object):
    def __init__(self, tokens, pattern):
        self.filename, self.line_num, self.text = tokens
        self.line_num = int(self.line_num)
        self.column = self.text.index(pattern)

    @staticmethod
    def create(line, pattern):
        tokens = line.split(':', 2)
        if len(tokens) != 3:
            return None
        return Match(tokens, pattern)

    def __unicode__(self):
        tokens = [self.filename, self.line_num, self.column, self.text]
        return u':'.join(map(unicode, tokens))

    def __str__(self):
        return str(unicode(self))

def check_install():
    for cmd in ['mkid', _get_gid_cmd()]:
        ret = os.system('which %s > /dev/null' % cmd)
        if ret != 0:
            msg = (
                "The program '%s' is currently not installed.  "
                "You can install it by typing:\n" % cmd
            )
            if platform.system() == 'Darwin':
                msg += "sudo port install idutils"
            else:
                msg += "sudo apt-get install id-utils"
            print msg
            sys.exit(1)

def get_list(patterns=None):
    if patterns is None:
        patterns = get_list.original_patterns
    first_pattern = patterns[0]

    lines = _gid(first_pattern)
    matches = [Match.create(line, first_pattern) for line in lines]
    matches = [m for m in matches if m]

    for pattern in patterns[1:]:
        matches = _filter_pattern(matches, pattern)

    return matches

get_list.original_patterns = []

def filter_until_select(matches, patterns, last_n):
    '''
    Return:
        >0: selected number.
         0: normal exit.
        <0: error.
    '''
    matches = matches[:]  # Make a clone.

    # Enter interactive mode.
    if not hasattr(filter_until_select, 'fold'):
        filter_until_select.fold = False
    while True:
        if not matches:
            print 'No file matched.'
            return 0, matches, patterns

        _show_list(matches, patterns, last_n, filter_until_select.fold)
        msg = (
            '\nSelect an action:'
            '\n* Input number to select a file.'
            '\n* Type "%s" / "%s" to keep / remove statements.'
            '\n* Type "%s" to switch between all matches and fold matches.'
            '\n* Type STRING (regex) to filter filename. !STRING means exclude '
            'the matched filename: '
            '\n* Type %s[PATTERN1 PATTERN2 ~PATTERN3 ...] to start over. '
            '\n  Type only "%s" to use the patterns from the command line.'
            '\n* Type ENTER to exit.'
            '\n'
            '\n>> ' % (A_KEEP_STATEMENT, A_CLEAN_STATEMENT,
                       A_FOLD, A_RESTART, A_RESTART)
        )
        response = raw_input(msg).strip()
        if not response:
            return 0, matches, patterns

        if re.match('\d+', response):
            break

        # Clean/Keep statements
        if response in [A_CLEAN_STATEMENT, A_KEEP_STATEMENT]:
            matches = _filter_statement(matches, response == A_CLEAN_STATEMENT)
            continue

        if response == A_FOLD:
            filter_until_select.fold = not filter_until_select.fold
            continue

        if response[0] == A_RESTART:
            if len(response) == 1:
                matches = get_list()
            else:
                patterns = response[1:].split()
                matches = get_list(patterns)
            continue

        # Clean/Keep based on filename
        if response[0] == '!':
            exclude = True
            response = response[1:]
        else:
            exclude = False
        matches = _filter_filename(matches, response, exclude)

    # Parse the selected number
    try:
        n = int(response)
    except ValueError, e:
        print 'Invalid input.'
        return -1, matches, patterns

    if n < 1 or n > len(matches):
        print 'Invalid input.'
        return -1, matches, patterns

    return n, matches, patterns

def find_declaration_or_definition(pattern):
    if pattern.startswith('m_') or pattern.startswith('s_'):
        # For non-static member fields or static member fields,
        # find symobls in header files.
        matches = get_list([pattern])
        return _filter_filename(matches, '\.h$', False)

    matches = tuple(get_list([pattern]))
    # Find declaration if possible.
    result = []
    for type_ in ('class', 'struct', 'enum'):
        tmp = _filter_pattern(matches, type_)
        tmp = _filter_statement(tmp, True)
        result += tmp
    result += _filter_pattern(matches, 'typedef')
    result += _filter_pattern(matches, 'define')
    # Find definition if possible.
    result += _keep_definition(matches, pattern)
    return result

#-----------------------------------------------------------
# private
#-----------------------------------------------------------
def _get_gid_cmd():
    gid = 'gid'
    if platform.system() == 'Darwin':
        gid = 'gid32'
    return gid

def _gid(pattern):
    cmd = [_get_gid_cmd(), pattern]
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    return process.stdout.read().decode('utf8').split('\n')

def _show_list(matches, patterns, last_n, fold):
    def yellow(text):
        return '\033[1;33m%s\033[0m' % text

    def yellow_background(text):
        return '\033[30;43m%s\033[0m' % text

    def green(text):
        return '\033[1;32m%s\033[0m' % text

    def red(text):
        return '\033[1;31m%s\033[0m' % text

    def black(text):
        return '\033[1;30m%s\033[0m' % text

    os.system('clear')
    last_filename = ''
    for i, m in enumerate(matches):
        if fold and m.filename == last_filename:
            continue

        last_filename = m.filename
        i += 1
        if i == last_n:
            print black('(%s) %s:%s:%s' % (i, m.line_num, m.filename, m.text))
        else:
            for pattern in patterns:
                code = m.text.replace(pattern, yellow_background(pattern))
            print '(%s) %s:%s:%s' % (red(i), yellow(m.line_num), green(m.filename), code)

def _filter_statement(all_, exclude):
    matches = [m for m in all_ if re.search(';\s*$', m.text)]
    if not exclude:
        return matches
    return _subtract_list(all_, matches)

def _filter_filename(all_, pattern, exclude):
    matched = [m for m in all_ if re.search(pattern, m.filename)]
    if not exclude:
        return matched
    return _subtract_list(all_, matched)

def _filter_pattern(matches, pattern):
    negative_symbol = '~'

    new_matches = []
    new_pattern = pattern[1:] if pattern.startswith(negative_symbol) else pattern
    for m in matches:
        matched = not not re.search('\\b%s\\b' % new_pattern, m.text)
        if pattern.startswith(negative_symbol):
            matched = not matched
        if matched:
            new_matches.append(m)

    return new_matches

def _filter_filename(all_, pattern, exclude):
    matched = [m for m in all_ if re.search(pattern, m.filename)]
    if not exclude:
        return matched
    return _subtract_list(all_, matched)

def _subtract_list(kept, removed):
    return [e for e in kept if e not in removed]

def _keep_definition(all_, pattern):
    new_pattern = ':%s(' % pattern
    return [m for m in all_ if new_pattern in m.text]
