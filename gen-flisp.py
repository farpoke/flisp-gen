
from collections import OrderedDict
from pprint import pprint
import re


flisp_specification = OrderedDict([
    ('basic', OrderedDict([
        ('RESET', OrderedDict([
            ('Q0', ['F1', 'F0', 'LDR']),
            ('Q1', ['OER', 'LDTA']),
            ('Q2', ['MR', 'G14', 'LDPC'])
        ])),
        ('FETCH', OrderedDict([
            ('Q3', ['MR', 'CLRT', 'LDI', 'INCPC'])
        ])),
        ('00 : NOP', OrderedDict([
            ('I00', OrderedDict([
                ('Q4', ['NF'])
            ]))
        ]))
    ]))
])


def parse_section_specification(original_text, section):

    def starts_with_group(text):
        match = re.match(r'^\s*(\w+|".+?"|\'.+?\')\s*\(', text)
        if match is not None:
            literal = match.group(1)
            if literal[0] in ('"', "'"):
                literal = '(' + literal[1:-1] + ')'
            return True, literal, text[match.end():]
        else:
            return False, None, text

    def starts_with_literal(text):
        match = re.match(r'^\s*(\w+|".+?"|\'.+?\')\s*[^(]', text)
        if match is not None:
            literal = match.group(1)
            if literal[0] in ('"', "'"):
                literal = '(' + literal[1:-1] + ')'
            return True, literal, text[match.end()-1:]
        else:
            return False, None, text

    def starts_with_end_group(text):
        match = re.match(r'^\s*\)', text)
        if match is not None:
            return True, None, text[match.end():]
        else:
            return False, None, text

    def starts_with_comment(text):
        match = re.match(r'^\s*/\*.*?\*/', text)
        if match is not None:
            return True, None, text[match.end():]
        else:
            return False, None, text

    stack = [section]
    text = original_text.strip()
    while len(text) > 0:
        matched, literal, text = starts_with_group(text)
        if matched:
            new_dict = OrderedDict()
            stack[-1][literal] = new_dict
            stack.append(new_dict)
            continue
        matched, literal, text = starts_with_literal(text)
        if matched:
            stack[-1][literal] = None
            continue
        matched, literal, text = starts_with_end_group(text)
        if matched:
            if len(stack) == 1:
                raise RuntimeError('Invalid specification, unmatched parentheses: ' + original_text)
            stack.pop()
            continue
        matched, literal, text = starts_with_comment(text)
        if matched:
            continue
        raise RuntimeError('Invalid specification: ' + original_text)
    if len(stack) != 1:
        raise RuntimeError('Invalid specification, unmatched parentheses: ' + original_text)


def parse_meta_flisp(file):
    specification = OrderedDict()
    current_file = None
    current_section = None
    text_accumulator = ''
    while True:
        line = file.readline()
        if line == '':
            break
        line = line.strip()
        if line == '':
            continue
        print('META FLISP >>', line)
        match = re.match(r'^([^%]*?)\s*(%.*)?$', line)
        line = match.group(1)
        #
        file_match = re.match(r'\s*<([^\]]+)>', line)
        if file_match is not None:
            if current_section is not None:
                parse_section_specification(text_accumulator, current_section)
                text_accumulator = ''
            file_name = file_match.group(1).strip()
            if file_match in specification:
                raise RuntimeError('Duplicate file name: ' + file_name)
            current_file = OrderedDict()
            specification[file_name] = current_file
            current_section = None
            print('Reading file specificaion', file_name)
            continue
        elif current_file is None:
            raise RuntimeError('Malformed META FLISP; no file specified.')
        #
        section_match = re.match(r'\s*\[([^\]]+)\]', line)
        if section_match is not None:
            if current_section is not None:
                parse_section_specification(text_accumulator, current_section)
                text_accumulator = ''
            section_name = section_match.group(1).strip()
            if section_match in specification:
                raise RuntimeError('Duplicate section name: ' + section_name)
            current_section = OrderedDict()
            current_file[section_name] = current_section
            text_accumulator = ''
            print('Reading section specification', section_name)
            continue
        elif current_section is None:
            raise RuntimeError('Malformed META FLISP; no file specified.')
        #
        text_accumulator += line + ' '
    if current_section is not None:
        parse_section_specification(text_accumulator, current_section)
    return specification


def meta_print(*args, **kwargs):
    print(*args, **kwargs)
    if 'file' in kwargs:
        file = kwargs['file']
        del kwargs['file']
        print(file.name, '<<', *args, **kwargs)


def generate_subfile(name, specification):
    with open(name + '.hwflisp', 'w') as flisp_file:
        meta_print('Konfigurationsfil: "%s.hwflisp"' % name, file=flisp_file)
        meta_print('Genererad av FLISP-gen (c) Anton Mårtensson', file=flisp_file)
        for section_name, section_specification in specification.items():
            meta_print(file=flisp_file)
            meta_print('-' * 80, file=flisp_file)
            meta_print(section_name, file=flisp_file)
            meta_print('-' * 80, file=flisp_file)

            def output_mergestate(prefix, item):
                first = True
                for subitem_key, subitem_value in item.items():
                    if subitem_value is None:
                        meta_print('# MergeState %s=\t(%s)' % (subitem_key, prefix), file=flisp_file)
                    else:
                        new_prefix = subitem_key if prefix == '' else subitem_key + '*' + prefix
                        if first:
                            first = False
                        else:
                            meta_print('-', file=flisp_file)
                        output_mergestate(new_prefix, subitem_value)

            output_mergestate('', section_specification)


def generate_flisp(specification):
    with open('flisp.hwflisp', 'w') as flisp_file:
        meta_print('FLISP huvudkonfigurationsfil FLISP.HWFLISP', file=flisp_file)
        meta_print('Konfigurering av fast styrenhet i FLISP', file=flisp_file)
        meta_print('Genererad av FLISP-gen (c) Anton Maartensson', file=flisp_file)
        meta_print(file=flisp_file)
        for subfile, subfile_specification in specification.items():
            meta_print('# Load "%s.hwflisp"' % subfile, file=flisp_file)
            generate_subfile(subfile, subfile_specification)


def run():
    #generate_flisp(flisp_specification)
    with open('meta-flisp.txt', 'r') as meta_flisp:
        specification = parse_meta_flisp(meta_flisp)
    if False:
        pprint(specification)
    generate_flisp(specification)


if __name__ == '__main__':
    run()
