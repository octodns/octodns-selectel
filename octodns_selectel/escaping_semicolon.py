def escape_semicolon(s):
    return s.replace(';', '\\;')


def unescape_semicolon(s):
    return s.replace('\\;', ';')
