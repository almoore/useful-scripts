import re


class DebianComparisonException(Exception):
    pass


def debian_digit_compare(a, b):
    if a == b:
        return 0
    normalized_a = a.lstrip().rstrip().lstrip("0")
    normalized_b = b.lstrip().rstrip().lstrip("0")
    if len(normalized_a) != len(normalized_b):
        return len(normalized_a) - len(normalized_b)
    else:
        if normalized_a < normalized_b:
            return -1
        elif normalized_b > normalized_a:
            return 1
        else:
            return 0


def debian_lex_compare(a, b):
    if a == b:
        return 0
    len_a = len(a)
    len_b = len(b)
    smaller_length = min(len_a, len_b)
    for i in range(0, smaller_length):
        if a[i] == "~" and b[i] != "~":
            return -1
        elif a[i] != "~" and b[i] == "~":
            return 1
        elif a[i].isalpha() and not b[i].isalpha():
            return -1
        elif not a[i].isalpha() and b[i].isalpha():
            return 1
        elif a[i] != b[i]:
            if a[i] < b[i]:
                return -1
            elif a[i] > b[i]:
                return 1
            else:
                raise DebianComparisonException("This is impossible")
    if len_a == len_b:
        return 0
    elif len_a == smaller_length:
        if b[smaller_length] == "~":
            return 1
        else:
            return -1
    elif len_b == smaller_length:
        if a[smaller_length] == "~":
            return -1
        else:
            return 1
    else:
        raise DebianComparisonException("This is impossible")


deb_find_nondigits = re.compile(r"^(?P<nondigits>[^0-9]*)(?P<residue>.*)$")
deb_find_digits = re.compile(r"^(?P<digits>[0-9]*)(?P<residue>.*)$")
deb_find_epoch = re.compile(r"^[0-9]+:")


def debian_normalize(a):
    clean_a = a.lstrip().rstrip()
    if not deb_find_epoch.search(clean_a):
        a_with_epoch = "0:" + clean_a
    else:
        a_with_epoch = str(clean_a)
    return a_with_epoch


def debian_compare(a, b):
    normal_a = debian_normalize(a)
    normal_b = debian_normalize(b)
    if normal_a == normal_b:
        return 0
    a_residue = str(normal_a)
    b_residue = str(normal_b)
    while len(a_residue) > 0 or len(b_residue) > 0:
        a_parts = deb_find_nondigits.search(a_residue).groupdict()
        a_nondigits = a_parts["nondigits"]
        a_residue = a_parts["residue"]
        b_parts = deb_find_nondigits.search(b_residue).groupdict()
        b_nondigits = b_parts["nondigits"]
        b_residue = b_parts["residue"]
        lex_compare = debian_lex_compare(a_nondigits, b_nondigits)
        if lex_compare != 0:
            return lex_compare
        a_parts = deb_find_digits.search(a_residue).groupdict()
        a_digits = a_parts["digits"]
        a_residue = a_parts["residue"]
        b_parts = deb_find_digits.search(b_residue).groupdict()
        b_digits = b_parts["digits"]
        b_residue = b_parts["residue"]
        digit_compare = debian_digit_compare(a_digits, b_digits)
        if digit_compare != 0:
            return digit_compare

    return 0
