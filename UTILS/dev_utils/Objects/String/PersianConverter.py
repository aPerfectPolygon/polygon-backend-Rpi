import urllib.parse
from .main import replace2


def tofa(data: str) -> str:
    data = ar2fa_num(data)
    data = ar2fa_char(data)
    data = en2fa_num(data)
    # data = en2fa_char(data)

    return data


def en2fa_num(data: str) -> str:
    """
    Converts English numbers to Persian numbers
    """
    mapping = {
        '0': '۰',
        '1': '۱',
        '2': '۲',
        '3': '۳',
        '4': '۴',
        '5': '۵',
        '6': '۶',
        '7': '۷',
        '8': '۸',
        '9': '۹',
        '.': '.',
    }
    return replace2(data, mapping)


def en2fa_char(data: str) -> str:
    """
        Assumes that characters written with standard persian keyboard
        not windows arabic layout
    """
    mapping = {
        'q': 'ض',
        'w': 'ص',
        'e': 'ث',
        'r': 'ق',
        't': 'ف',
        'y': 'غ',
        'u': 'ع',
        'i': 'ه',
        'o': 'خ',
        'p': 'ح',
        '[': 'ج',
        ']': 'چ',
        'a': 'ش',
        's': 'س',
        'd': 'ی',
        'f': 'ب',
        'g': 'ل',
        'h': 'ا',
        'j': 'ت',
        'k': 'ن',
        'l': 'م',
        ';': 'ک',
        "'": 'گ',
        'z': 'ظ',
        'x': 'ط',
        'c': 'ز',
        'v': 'ر',
        'b': 'ذ',
        'n': 'د',
        'm': 'پ',
        ',': 'و',
        '?': '؟',
    }
    return replace2(data, mapping)


def ar2fa_num(data: str) -> str:
    """
    Converts Arabic numbers to Persian numbers
    """
    mapping = {
        '١': '۱',  # Arabic 1 is 0x661 and Persian one is 0x6f1
        '٢': '۲',  # More info https://goo.gl/SPiBtn
        '٣': '۳',
        '٤': '۴',
        '٥': '۵',
        '٦': '۶',
        '٧': '۷',
        '٨': '۸',
        '٩': '۹',
        '٠': '۰',
    }
    return replace2(data, mapping)


def fa2en_num(data: str) -> str:
    """
    Converts Persian numbers to English numbers.
    """
    mapping = {
        '۰': '0',
        '۱': '1',
        '۲': '2',
        '۳': '3',
        '۴': '4',
        '۵': '5',
        '۶': '6',
        '۷': '7',
        '۸': '8',
        '۹': '9',
        '.': '.',
    }
    return replace2(data, mapping)


def ar2fa_char(data: str) -> str:
    """
    Converts Arabic chars to related Persian unicode char
    """
    mapping = {
        'ك': 'ک',
        'دِ': 'د',
        'بِ': 'ب',
        'زِ': 'ز',
        'ذِ': 'ذ',
        'شِ': 'ش',
        'سِ': 'س',
        'ى': 'ی',
        'ي': 'ی'
    }
    return replace2(data, mapping)


def zwnj(data: str) -> str:
    mapping = {
        '\u200c': ' '
    }
    return replace2(data, mapping)


def url_decode(data: str) -> str:
    """
    Decode Persian characters in URL
    """
    return urllib.parse.unquote(data)
