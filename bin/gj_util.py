#!/usr/bin/env python
# -*- encoding: utf8 -*-

try:
    import cPickle as pickle
except Exception as e:
    # Python 3 doesn't have cPickle.
    import pickle

import os
import platform
import re
import subprocess
import sys


__author__ = 'fcamel'

#------------------------------------------------------------------------------
# Configuration
#------------------------------------------------------------------------------

LANG_MAP_FILE         = "id-lang.map"
DEFINITION_INDEX_FILE = 'gj.index'
CONFIG_FILE           = '.gjconfig'

# Input mappings
A_KEEP_STATEMENT       = ';'
A_CLEAN_STATEMENT      = '!;'
A_FOLD                 = '.'
A_RESTART              = '~'

ENABLE_COLOR_OUTPUT = not sys.stdout.isatty()

DEFAULT_CODE_LENGTH = 80

DEBUG = False

config = {
    'search_extended_lines': 0,
    'verbose': False,
    'db_path': 'ID',
}

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

    @staticmethod
    def sort_key(match):
        return (match.filename, match.line_num)

    def __unicode__(self):
        tokens = [self.filename, self.line_num, self.column, self.text]
        return u':'.join(map(unicode, tokens))

    def __str__(self):
        return str(unicode(self))

    def is_golang(self):
        return self.filename.endswith('.go')


# Used by finding definition.
class FileLine(object):
    def __init__(self, path, line):
        self.path = path
        self.line = line

    def __eq__(self, other):
        return self.path == other.path and self.line == other.line

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return '%s:%d' % (self.path, self.line)

    def __repr__(self):
        return str(self)


# Used by finding definition.
class SymbolInfo(object):
    @staticmethod
    def sort_key(info):
        return (info.symbol, info.full)

    def __init__(self, symbol, full, fileline):
        self.symbol = symbol
        self.full = full
        self.fileline = fileline

    def __eq__(self, other):
        return (self.symbol == other.symbol and self.full == other.full
                and self.fileline == other.fileline)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return '(%s, %s, %s)' % (self.symbol, self.full, self.fileline)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.full)


def check_install():
    for cmd in ['mkid', _get_gid_cmd()]:
        if not _is_cmd_exists(cmd):
            msg = (
                "The program '%s' is currently not installed.  "
                "You can install it by typing:\n" % cmd
            )
            install_cmd = _get_idutils_install_cmd()
            if install_cmd:
                msg += install_cmd
            else:
                msg += "  (Unknown package manager. Try to install id-utils anyway.)\n"
                msg += "  (http://www.gnu.org/software/idutils/)"
            print(msg)
            sys.exit(1)

def build_index(db_path):
    lang_path = os.path.join(os.path.dirname(__file__), LANG_MAP_FILE)
    return _mkid(lang_path, db_path)


def _find_matches(pattern):
    lines = _gid(pattern)
    # gid may get unmatched pattern when the argument is a number.
    # Don't know the reason. Manually filter unmatched lines.
    # This fix also supports searching "pattern()" or "pattern("
    # which is useful to find all function calls.
    candidated_lines = []
    for line in lines:
        tokens = line.split(':', 2)
        if len(tokens) == 3 and pattern in tokens[2]:
            candidated_lines.append(line)
    matches = [Match.create(line, pattern) for line in candidated_lines]
    return [m for m in matches if m]


def find_matches(patterns=None, filter_='', path_prefix=''):
    if patterns is None:
        patterns = find_matches.original_patterns
    matches = _find_matches(patterns[0])
    for pattern in patterns[1:]:
        matches = _filter_matches(matches, pattern)

    if path_prefix:
        matches = _filter_filename(matches, '^' + path_prefix, False)

    if filter_:
        matches_by_filter = _find_matches(filter_)
        filenames = set(m.filename for m in matches_by_filter)
        matches = [m for m in matches if m.filename in filenames]

    return sorted(matches, key=Match.sort_key)

find_matches.original_patterns = []

def choose_matches_interactively(matches, patterns):
    matches = matches[:]  # Make a clone.

    if not hasattr(choose_matches_interactively, 'fold'):
        choose_matches_interactively.fold = False

    if not hasattr(choose_matches_interactively, 'selections'):
        choose_matches_interactively.selections = []

    # Enter the interactive mode.
    while True:
        if not matches:
            print('No file matched.')
            return [], matches, patterns

        matches = sorted(set(matches), key=Match.sort_key)
        index_mapping = _show_list(matches,
                                   patterns,
                                   choose_matches_interactively.selections,
                                   choose_matches_interactively.fold)
        global input
        try:
            input = raw_input
        except NameError:
            pass

        response = None
        try:
            response = input(_get_prompt_help()).strip()
        except (EOFError, KeyboardInterrupt) as e:
            print('')

        if not response:
            return [], matches, patterns

        if re.match('\d+', response):
            break

        # Clean/Keep statements
        if response in [A_CLEAN_STATEMENT, A_KEEP_STATEMENT]:
            matches = _filter_statement(matches, response == A_CLEAN_STATEMENT)
            continue

        if response == A_FOLD:
            choose_matches_interactively.fold = not choose_matches_interactively.fold
            continue

        if response[0] == A_RESTART:
            if len(response) == 1:
                matches = find_matches()
            else:
                patterns = response[1:].split()
                matches = find_matches(patterns)
            continue

        # Clean/Keep based on filename
        if response[0] == '!':
            exclude = True
            response = response[1:]
        else:
            exclude = False
        matches = _filter_filename(matches, response, exclude)

    matches.sort(key=Match.sort_key)

    # Parse the selected number
    input_numbers = parse_number(response)
    if not input_numbers:
        print('Invalid input.')
        return None, matches, patterns

    numbers = []
    for n in input_numbers:
        n = index_mapping.get(n, -1)
        if n < 0 or n >= len(matches):
            print('Invalid input.')
            return None, matches, patterns
        numbers.append(n)

    choose_matches_interactively.selections = numbers

    return [matches[n] for n in numbers], matches, patterns

def find_declaration_or_definition(pattern, path_prefix=''):
    if pattern.startswith('m_') or pattern.startswith('s_'):
        # For non-static member fields or static member fields,
        # find symobls in header files.
        matches = find_matches([pattern])
        return _filter_filename(matches, '\.h$', False)

    matches = tuple(find_matches([pattern]))

    if path_prefix:
        matches = _filter_filename(matches, '^' + path_prefix, False)

    # Find declaration if possible.
    result = set()
    types = (
        'class',
        'struct',
        'enum',
        'interface',  # Java, Objective C
    )
    for type_ in types:
        tmp = _filter_matches(matches, type_)
        tmp = _filter_statement(tmp, True)
        result.update(tmp)
    result.update(_filter_matches(matches, 'typedef'))
    result.update(_filter_matches(matches, 'define'))
    result.update(_filter_matches(matches, 'using'))
    # Find definition if possible.
    result.update(_keep_possible_definition(matches, pattern))

    # Special handling for Golang.
    # 1. Remove all matches from the general rules.
    result = set(r for r in result if not r.is_golang())

    # 2. Apply customized rules.
    result.update(_filter_declaration_or_definitions_for_golang(matches, pattern))

    return sorted(result, key=Match.sort_key)

def find_definition(symbol):
    result = []
    with open(DEFINITION_INDEX_FILE, 'rb') as fr:
        # format: [(symbol, offset)]
        info_index = pickle.load(fr)
        begin = 0
        end = len(info_index)
        index_offset = fr.tell()
        for i, (s, offset) in enumerate(info_index):
            if s > symbol:
                end = i
                break
        for i in range(end - 1, 0, -1):
            if info_index[i][0] < symbol:
                begin = i
                break

        for i in range(begin, end):
            fr.seek(index_offset + info_index[i][1])
            infos = pickle.load(fr)
            for info in infos:
                if info.symbol == symbol:
                    string = '%s:%d:%s' % (info.fileline.path, info.fileline.line, info.full)
                    match = Match.create(string, symbol)
                    result.append(match)

    return sorted(result, key=Match.sort_key)

def find_symbols(pattern, path_pattern=''):
    global config

    verbose = config['verbose']
    if path_pattern:
        verbose = True

    args = ['-lis']
    if not verbose:
        args.extend(('-R', 'none'))
    lines = _lid(pattern, args)
    result = []
    max_width = 120
    indent = 8
    for line in lines:
        tokens = line.split()
        if path_pattern:
            paths = tokens[1:]
            matched = False
            for p in paths:
                if path_pattern in p:
                    matched = True
                    break
            if not matched:
                continue

        if len(line) < max_width:
            result.append(line)
            continue

        first_line = True
        current_length = 0
        ts = []
        for i, tk in enumerate(tokens):
            if i and path_pattern and path_pattern not in tk:
                # Filter non-matched file paths
                continue
            length = len(tk)
            if current_length + length > max_width:
                prefix = '' if first_line else ' ' * indent
                result.append(prefix + ' '.join(ts))
                ts = []
                first_line = False
                current_length = indent;
                length = len(tk)

            ts.append(tk)
            current_length += length

        if ts:
            prefix = '' if first_line else ' ' * indent
            result.append(prefix + ' '.join(ts))

    tmp =  [_highlight(pattern, line) for line in result if line]
    if path_pattern:
        tmp = [_highlight(path_pattern, line, level=1) for line in tmp if line]
    return tmp

#-----------------------------------------------------------
# private
#-----------------------------------------------------------
def _mkid(lang_file, db_path):
    cmd = ['mkid', '-m', lang_file, '-f', db_path]
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout = process.stdout.read()
    stderr = process.stderr.read()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    return True

def _is_cmd_exists(cmd):
    return 0 == subprocess.call(['which', cmd],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

def _get_idutils_install_cmd():
    if platform.system() == 'Darwin':
        mgrs = {
               'port': "sudo port install idutils", # MacPorts
               'brew': "brew install idutils",      # Homebrew
            }
        for mgr, cmd in mgrs.items():
            if _is_cmd_exists(mgr):
                return cmd
        return ""
    else:
        return "sudo apt-get install id-utils"

def _get_gid_cmd():
    gid = 'gid'
    if platform.system() == 'Darwin':
        if _is_cmd_exists('gid32'):
            gid = 'gid32'
    return gid

def _execute(args):
    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    text = process.stdout.read()
    try:
        text = text.decode('utf8')
    except Exception as e:
        if DEBUG:
            print('-' * 80)
            print('\ntext: <%s>\nreturns non-utf8 result.' % text)
            print('-' * 80)
        result = []
        for line in text.split('\n'):
            try:
                line = line.decode('utf8')
                result.append(line)
            except Exception as e:
                if DEBUG:
                    print('-' * 80)
                    print('%s: skip <%s>' % (e, line))
                    print('-' * 80)
        return result
    return text.split('\n')

def _gid(pattern):
    global config

    # Support searching "FUNCTION(" or "FUNCTION()".
    # () has special meaning for gid. Do not pass it to gid.
    if pattern.endswith('('):
        pattern = pattern[:-1]
    elif pattern.endswith('()'):
        pattern = pattern[:-2]
    cmd = [_get_gid_cmd(), '-f', config['db_path'], pattern]
    return _execute(cmd)

def _lid(pattern, args):
    global config

    cmd = ['lid', '-f', config['db_path']] + args + [pattern]
    return _execute(cmd)

def _highlight(pattern, text, level=2):
    def red(text):
        if sys.stdout.isatty():
            return '\033[1;31m%s\033[0m' % text
        else:
            return text

    def green(text):
        if sys.stdout.isatty():
            return '\033[1;32m%s\033[0m' % text
        else:
            return text

    # Find all begin indexes of case-insensitive substring.
    begins = []
    base = 0
    pl = pattern.lower()
    tl = text.lower()
    while True:
        try:
            offset = tl.index(pl)
            begins.append(base + offset)
            tl = tl[offset + len(pl):]
            base += offset + len(pl)
        except Exception as e:
            break

    if not begins:
        return text

    # Highlight matched case-insensitive substrings.
    result = []
    last_end = 0
    for begin in begins:
        if begin > last_end:
            result.append(text[last_end:begin])
        end = begin + len(pattern)
        if level >= 2:
            result.append(red(text[begin:end]))
        else:
            result.append(green(text[begin:end]))
        last_end = end
    if last_end < len(text):
        result.append(text[last_end:])

    return ''.join(result)

def _show_list(matches, patterns, selections, fold):
    def yellow(text):
        if sys.stdout.isatty():
            return '\033[1;33m%s\033[0m' % text
        else:
            return text

    def green(text):
        if sys.stdout.isatty():
            return '\033[1;32m%s\033[0m' % text
        else:
            return text

    def red(text):
        if sys.stdout.isatty():
            return '\033[1;31m%s\033[0m' % text
        else:
            return text

    def black(text):
        if sys.stdout.isatty():
            return '\033[1;30m%s\033[0m' % text
        else:
            return text

    global config

    os.system('clear')
    last_filename = ''
    index_mapping = {}
    user_index = 1
    for i, m in enumerate(matches):
        if fold and m.filename == last_filename:
            continue

        last_filename = m.filename
        if i in selections:
            print(black('(%s) %s:%s:%s' % (user_index, m.line_num, m.filename, m.text)))
        else:
            code = m.text
            if not config['verbose'] and len(code) > DEFAULT_CODE_LENGTH:
                code = code[:DEFAULT_CODE_LENGTH] + " ..."
            for pattern in patterns:
                code = _highlight(pattern, code)
            print('(%s) %s:%s:%s' % (red(user_index), yellow(m.line_num), green(m.filename), code))

        index_mapping[user_index] = i
        user_index += 1

    return index_mapping

def _filter_statement(all_, exclude):
    matches = [m for m in all_ if re.search(';\s*$', m.text)]
    if not exclude:
        return matches
    return _subtract_list(all_, matches)

def _filter_matches(matches, pattern):
    global config

    negative_symbol = '~'

    new_matches = []
    new_pattern = pattern[1:] if pattern.startswith(negative_symbol) else pattern
    for m in matches:
        # Special case: find the assignment operation and exclude equality operators.
        if config['search_extended_lines'] > 0:
            lines = []
            with open(m.filename) as fr:
                i = 0
                for line in fr:
                    i += 1
                    if abs(i - m.line_num) > config['search_extended_lines']:
                        continue
                    lines.append(line.strip())
            text = '\n'.join(lines)
        else:
            text = m.text
        if new_pattern == '=':
            matched = not not re.search('[^=]=[^=]', text)
            if not matched:
                matched = not not re.search('[^=]=$', text)
        else:
            matched = not not re.search('\\b%s\\b' % new_pattern, text)
        if pattern.startswith(negative_symbol):
            matched = not matched
        if matched:
            new_matches.append(m)

    return new_matches

def _filter_declaration_or_definitions_for_golang(matches, pattern):
    new_matches = []
    for m in matches:
        if not m.is_golang():
            continue

        text = m.text.strip()
        if re.match('func (\(.+\) )?%s\(.*{(.*})?$' % pattern, text):
            new_matches.append(m)
        elif re.match('func (\(.+\) )?%s\(.*,$' % pattern, text):
            # arguments too long, end with some argument.
            new_matches.append(m)
        elif re.match('func \(.+ \*?%s\) [a-zA-Z][a-zA-Z0-9]*\(.*$' % pattern, text):
            # |pattern|'s methods
            new_matches.append(m)
        elif text.endswith(pattern + ' struct {'):
            new_matches.append(m)
        elif text.startswith('var ' + pattern) or text.startswith('const ' + pattern):
            new_matches.append(m)
    return new_matches

def _filter_filename(all_, pattern, exclude):
    matched = [m for m in all_ if re.search(pattern, m.filename)]
    if not exclude:
        return matched
    return _subtract_list(all_, matched)

def _subtract_list(kept, removed):
    return [e for e in kept if e not in removed]

def _keep_possible_definition(all_, pattern):
    result = set()

    # C++: "::METHOD(...)"
    new_pattern = '::%s(' % pattern
    result.update(m for m in all_ if new_pattern in m.text)

    # C++: "METHOD() { ... }"
    new_pattern = pattern + ' *\(.*{.*}.*$'
    result.update(m for m in all_ if re.search(new_pattern, m.text))

    # Python: "def METHOD"
    new_pattern = 'def +' + pattern
    result.update(m for m in all_ if re.search(new_pattern, m.text))

    return result

def _find_possible_filename(pattern):
    def to_camelcase(word):
        '''
        Ref. http://stackoverflow.com/questions/4303492/how-can-i-simplify-this-conversion-from-underscore-to-camelcase-in-python
        '''
        return ''.join(x.capitalize() or '_' for x in word.split('_'))

    def to_underscore(name):
        '''
        Ref. http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case/1176023#1176023
        '''
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    if re.search('[A-Z]', pattern):  # assume it's a camcelcase pattern
        return (to_underscore(pattern), pattern)
    else:  # assume it's an underscore pattern
        return (pattern, to_camelcase(pattern))

# TODO(fcamel): modulize filter actions and combine help message and filter actions together.
def _get_prompt_help():
    msg = (
        '\nSelect an action:'
        '\n* Input number to select a file. Multiple choices are allowed (e.g., type "1-3, 5")'
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
    return msg

def parse_number(line):
    '''
    Expected input:
        3
        3,5
        3, 5, 7-10
    '''
    ns = set()
    ts = line.split(',')
    for t in ts:
        try:
            ns.add(int(t))
            continue
        except Exception as e:
            pass

        m = re.match('(\d+)-(\d+)', t.strip())
        if m:
            from_, to = map(int, m.groups())
            ns.update(range(from_, to + 1))

    return sorted(ns)
