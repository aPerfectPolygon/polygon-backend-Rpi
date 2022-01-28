def encode(text: str) -> str:
    return ','.join(str(ord(c)) for c in text)


def decode(text: str) -> str:
    return ''.join(chr(int(i)) for i in text.split(','))
