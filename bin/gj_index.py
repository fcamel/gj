#!/usr/bin/env python3
# -*- encoding: utf8 -*-

try:
    import cPickle as pickle
except Exception as e:
    # Python 3 doesn't have cPickle.
    import pickle

import sys
import os
import optparse
import shutil
import subprocess
import tempfile

import gj_util

DEBUG = False

def _get_symbols_and_address_in_code_section(binary):
    proc = subprocess.Popen(['nm', '-C', binary], stdout=subprocess.PIPE)
    result = []
    lines = proc.stdout.read().split('\n')
    for line in lines:
        tokens = line.strip().split(' ', 2)
        if len(tokens) == 3 and len(tokens[1]) == 1 and tokens[1] in 'tTwW':
            address, symbol = tokens[0], tokens[2]
            # Remove the prefix "000..."
            for i, d in enumerate(address):
                if d != '0':
                    break
            # Match the address format of objdump.
            address = '0x' + address[i:]
            result.append((symbol, address))
    return result

def _get_addresses_and_file_lines(binary, addresses=None):
    # objdump (2.24 and 2.28) has a bug that "--wide" doesn't work because it never sets the flag "do_wide".
    # On the other hand, "readelf --wide" works.
    # Reference: binutils/dwarf.c display_debug_lines_decoded() and "const unsigned int MAX_FILENAME_LENGTH = 35;"
    #proc = subprocess.Popen(['objdump', '--dwarf=decodedline', '--wide', binary], stdout=subprocess.PIPE)
    proc = subprocess.Popen(['readelf', '--debug-dump=decodedline', '--wide', binary], stdout=subprocess.PIPE)
    result = []
    lines = proc.stdout.read().split('\n')
    cu_path = cu_filename = path = filename = None
    for line in lines:
        if len(line) > 0 and line[-1] == ':':
            # A new section with a new path.
            is_cu_path = False
            path = line[:-1]
            if path.startswith("CU: "): # A new compilation unit.
                is_cu_path = True
                path = path[4:]
            if path.startswith('/'):
                path = os.path.abspath(path)  # remove unnecessary "../"
            filename = os.path.basename(path)
            if is_cu_path:
                cu_path = path
                cu_filename = filename
            continue

        tokens = line.split()
        if len(tokens) != 3:
            continue

        target_filename, line, address = tokens
        line = int(line)
        # We'll end up OOM if there are too many addresses. Only keep the necessary addresses.
        if addresses is not None and address not in addresses:
            continue
        if target_filename != filename:
            if target_filename == cu_filename:
                path = cu_path
            else:
                sys.stderr.write(
                    'Warning: Skip unexpected filename <%s>. CU: <%s> and path: <%s>.\n'
                     % (target_filename, cu_path, path))
                continue

        result.append((address, gj_util.FileLine(path, line)))

    return result

def _remove_nested_parenthesis(string, left, right, keep_top):
    valid_tokens = []
    valid_begin = -1
    depth = 0
    for i, c in enumerate(string):
        if c == left:
            if depth == 0:
                if valid_begin >= 0:
                    valid_tokens.append(string[valid_begin:i])
                    if keep_top:
                        valid_tokens.append(left)
                    valid_begin = -1
            depth += 1
            continue

        if c == right:
            depth -= 1
            if depth == 0 and keep_top:
                valid_tokens.append(right)
            continue

        if depth == 0 and valid_begin < 0:
            valid_begin = i
    if valid_begin >= 0:
        valid_tokens.append(string[valid_begin:i + 1])

    return ''.join(valid_tokens)

def _get_symbol(full_symbol):
    if not full_symbol:
        return full_symbol

    # Examples:
    # * A B::C(D::E)       -> C
    # * A B::C             -> C
    # * A::B()::C::D()     -> D
    # * A::B<C::D>()       -> B
    # * A::B::operator()() -> operator()
    # * A::B::C((anonymous namespace))

    # Remove the templates ( <...> ).
    valid_full_symbol = _remove_nested_parenthesis(full_symbol, '<', '>', False)
    # Remove the nested parathenese ( () inside () ).
    valid_full_symbol = _remove_nested_parenthesis(valid_full_symbol, '(', ')', True)

    if 'operator()' in valid_full_symbol:
        # NOTE: inner class in operator()() is not handle.
        return 'operator()'

    ts = valid_full_symbol.split('(')
    target = ts[-2] if len(ts) > 2 else ts[0]
    return target.split('::')[-1]

def _update_index(binary, path_substituion, mapping):
    path_from, path_to = path_substituion
    # Load the debug info.
    symbols_and_addresses = _get_symbols_and_address_in_code_section(binary)
    addresses = set(a for _, a in symbols_and_addresses)
    addresses_and_filelines = _get_addresses_and_file_lines(binary, addresses)
    addresses_to_filelines = {}
    for addr, fl in addresses_and_filelines:
        if path_from is not None and fl.path.startswith(path_from):
            fl.path = path_to + fl.path[len(path_from):]
        addresses_to_filelines[addr] = fl

    # Map the debug info. Note that this is much faster than using "nm -l".
    # In my test case (167M binary with 250,000+ symbols),
    # "nm -l -C" hasn't finished after several minutes, while this approach takes <10s.
    for full_symbol, address in symbols_and_addresses:
        if full_symbol.startswith('non-virtual thunk'):
            continue

        fl = addresses_to_filelines.get(address, None)
        if fl is None:
            continue
        symbol = _get_symbol(full_symbol)
        info = gj_util.SymbolInfo(symbol, full_symbol, fl)
        data = mapping.get(symbol, None)
        if data is None:
            # First time.
            mapping[symbol] = info
            continue

        if type(data) is gj_util.SymbolInfo:
            # Second time.
            mapping[symbol] = set((data,))

        mapping[symbol].add(info)

def _find_shared_libraries(binary, shared_lib_sub_path):
    if not shared_lib_sub_path:
        return []

    result = []
    proc = subprocess.Popen(['ldd', binary], stdout=subprocess.PIPE)
    lines = proc.stdout.read().split('\n')
    for line in lines:
        # Example: "libcc.so => /path/to/libcc.so (0x00007fa842a83000)"
        if ' => ' not in line:
            continue

        shared_lib_path = line.strip().split()[2]
        if shared_lib_sub_path in shared_lib_path:
            result.append(shared_lib_path)
    return result

def _save(mapping, filename):
    infos = []
    for symbol in mapping:
        data = mapping[symbol]
        if type(data) is gj_util.SymbolInfo:
            infos.append(data)
            continue

        for info in data:
            infos.append(info)

    infos.sort(key=gj_util.SymbolInfo.sort_key)

    try:
        # The mapping may be very large (e.g., 300MB) and loading the whole file is slow.
        # Build the index, so we can only load necessary parts when searching.
        dirpath = tempfile.mkdtemp(prefix='gj_index_')
        info_index = []
        block_size = 1000
        n_filename = 0
        byte_offset = 0
        for i in range(0, len(infos), block_size):
            n_filename += 1
            path = os.path.join(dirpath, str(n_filename))
            with open(path, 'wb') as fw:
                pickle.dump(infos[i : i + block_size], fw)
            info_index.append((infos[i].symbol, byte_offset))
            byte_offset += os.stat(path).st_size

        with open(gj_util.DEFINITION_INDEX_FILE, 'wb') as fw:
            # Write the index first. Then write the data.
            pickle.dump(info_index, fw)

            # Write the info blocks in order.
            for i in range(1, n_filename + 1):
                path = os.path.join(dirpath, str(i))
                with open(path, 'rb') as fr:
                    fw.write(fr.read())
    finally:
        shutil.rmtree(dirpath)

def index_elf_binaries(binaries, substitution):
    for value in binaries:
        print(value, len(value))
        if len(value) != 2:
            print('Format error: expect each value in "binaries"'
                  ' is like ("out/debug/myprog", "out/debug")'
                  ' or ("out/debug/myprog", "")')
            return False

    mapping = {}
    for binary, shared_lib_sub_path in binaries:
        print('Index [%s] ...' % binary)
        _update_index(binary, substitution, mapping)
        for shared_lib in _find_shared_libraries(binary, shared_lib_sub_path):
            print('> Index shared library [%s] ...' % shared_lib)
            _update_index(shared_lib, substitution, mapping)


    if DEBUG:
        print('-' * 80)
        print('DEBUG: (Begin) Dump the result.')
        print('-' * 80)
        for symbol in mapping:
            print(mapping[symbol])
        print('-' * 80)
        print('DEBUG: (End  ) Dump the result.')
        print('-' * 80)

    _save(mapping, gj_util.DEFINITION_INDEX_FILE)

    print('Save the index to %s' % gj_util.DEFINITION_INDEX_FILE)

    return True

def main():
    '''\
    %prog [options] <binary> ...

    Index the function/method definitions' locations from binaries.
    '''
    global DEBUG

    parser = optparse.OptionParser(usage=main.__doc__)
    parser.add_option('-d', '--debug', dest='debug',
                      action='store_true', default=False,
                      help='Display debug messages (default: False).')
    parser.add_option('-s', '--substitue', dest='substitution',
                      type='string', default='',
                      help=('Given FROM=TO and substitue the prefix FROM in the path to TO.'
                            'For example, "../../=" removes the prefix "../../"'))
    options, args = parser.parse_args()

    if len(args) < 1:
        parser.print_help()
        return 1

    DEBUG = options.debug
    path_substitution = [None, None]
    if options.substitution:
         path_substitution = options.substitution.split('=')

    index_elf_binaries(args, path_substitution)

    return 0


if __name__ == '__main__':
    sys.exit(main())
