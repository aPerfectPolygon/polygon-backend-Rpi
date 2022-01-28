from UTILS import dev_utils
from UTILS.dev_utils import Log
import typing as ty


def pprint(*args, max_depth: int = 2, indent: int = 4, _curr_depth: int = 0, **kwargs) -> str:
    if not args:
        args = ['']

    output = []
    for item in args:
        if dev_utils.is_itterable(item):
            output.append(lprint(item, max_depth=max_depth, indent=indent, _curr_depth=_curr_depth))
        elif type(item) is dict:
            output.append(dprint(item, max_depth=max_depth, indent=indent, _curr_depth=_curr_depth))
        else:
            output.append(str(item))

    output = kwargs.pop('splitter', ',').join(output)

    if kwargs.pop('do_print', True):
        Log.Print(output, get_time=False, **kwargs)

    return output


def lprint(data: ty.Union[list, tuple], max_depth: int, indent: int, _curr_depth: int) -> str:
    if type(data) not in (list, tuple):
        return ''

    _sep = ','
    _curr_indenting = (indent * ' ') * _curr_depth
    _next_indenting = (indent * ' ') * (_curr_depth + 1)

    if _curr_depth > max_depth:
        return (_curr_indenting * _curr_depth) + str(data) + _sep

    output = []
    for item in data:
        if type(item) in (list, tuple):
            output.append(
                _next_indenting + lprint(item, max_depth, indent, _curr_depth + 1).strip()
            )
        elif type(item) is dict:
            output.append(
                _next_indenting + dprint(item, max_depth, indent, _curr_depth + 1).strip()
            )
        else:
            output.append(_next_indenting + str(item) + _sep)
    return _curr_indenting + '[\n' + '\n'.join(output) + '\n' + _curr_indenting + ']' + _sep


def dprint(data: dict, max_depth: int, indent: int, _curr_depth: int) -> str:
    if type(data) is not dict:
        return ''

    _sep = ','
    _sep_dict = ': '
    _curr_indenting = (indent * ' ') * _curr_depth
    _next_indenting = (indent * ' ') * (_curr_depth + 1)

    if _curr_depth > max_depth:
        return (_curr_indenting * _curr_depth) + str(data) + _sep

    output = []
    for k, v in data.items():
        if type(v) in (list, tuple):
            output.append(
                _next_indenting + str(k) + _sep_dict + lprint(v, max_depth, indent, _curr_depth + 1).strip()
            )
        elif type(v) is dict:
            output.append(
                _next_indenting + str(k) + _sep_dict + dprint(v, max_depth, indent, _curr_depth + 1).strip()
            )
        else:
            output.append(_next_indenting + str(k) + _sep_dict + str(v) + _sep)
    return _curr_indenting + '{\n' + '\n'.join(output) + '\n' + _curr_indenting + '}' + _sep


if __name__ == '__main__':
    x = {
        1: 2,
        3: [
            1, 2, {
                'a': [
                    'h', 'e'
                ]
            }
        ],
        5: {
            'x': 'v'
        }
    }
    pprint(x, max_depth=3, indent=1)
