#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  utils.py
#  This file is part of isbg.
#
#  Copyright 2018 Carles Muñoz Gorriz <carlesmu@internautas.org>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

# From https://docs.python.org/3/howto/logging-cookbook.html
# Get free of the pylint logging-format-interpolation warning using __

"""Utils for isbg - IMAP Spam Begone."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
from platform import python_version  # To check py version
from subprocess import Popen, PIPE   # To call Popen

try:
    # C implementation:
    import cchardet
except ImportError:
    try:
        # Pure python implementation:
        import chardet
    except ImportError:
        pass


def detect_enc(byte_sring):
    """Try to detect a encoding.

    It uses the ``cchardet`` and ``chardet`` modules to detect the encoding.
    If none of them are installed, it returns None.

    Args:
        byte_string (str | bytes): the byte string to detect.

    Return:
        dict: with at least the 'encoding' informed as returned by
            :py:func:`cchardet.detect` and :py:func:`chardet.detect`.

    """
    try:
        ret = cchardet.detect(byte_sring)
    except NameError:
        ret = None

    if not ret or 'encoding' not in ret or not ret['encoding'] or \
            ret['encoding'] == '':
        try:
            ret = chardet.detect(byte_sring)
        except NameError:
            pass

    if not ret or not ret['encoding']:
        return {'encoding': None}

    return ret


def hexdigit(char):
    """Tanslate a hexadecimal character his decimal (int) value.

    Args:
        char (str): A hexadecimal number in base 16.
    Returns:
        int: the base 10 representation of the number.

    Raises:
        ValueError: if `char` is not a valid hexadecimal character.

    """
    if char >= '0' and char <= '9':
        return ord(char) - ord('0')
    if char >= 'a' and char <= 'f':
        return 10 + ord(char) - ord('a')
    if char >= 'A' and char <= 'F':
        return 10 + ord(char) - ord('A')
    raise ValueError(repr(char) + " is not a valid hexadecimal digit")


def hexof(string):
    """Translate a string to a string with its hexadecimal value.

    Args:
        string (str): A string to be translated.
    Returns:
        str: The translated string.

    Examples:
        >>> isbg.utils.hexof('isbg')
        '69736267'

    """
    res = ""
    for i in string:
        res = res + ("%02x" % ord(i))
    return res


def dehexof(string):
    """Tanslate a hexadecimal string to his string value.

    Args:
        string (str): A string containing a hexadecimal.
    Returns:
        str: The translated string.

    """
    res = ""
    while string:
        res = res + chr(16 * hexdigit(string[0]) + hexdigit(string[1]))
        string = string[2:]
    return res


def get_ascii_or_value(value):
    """Try to convert the contents of value to ascii string.

    When the `value` cannot be converted to an ascii string, it returns the
    value.

    Args:
        value (dict, list, str): The value to convert.
    Returns:
        The `value` object with its contents translated if it was possible.

    Note:
        In `python3` we get the ``uids`` info as binary when using the
        methods of :py:class:`isbg.imaputils.IsbgImap4`.

        In `python2` if we get a `UnicodeDecodeError` we try first to get it
        in the detected encoded using the `cchardet` or `chardet` module.

    Examples:
        `Python2`:
            >>> get_ascii_or_value('isbg - IMAP Spam Begone')
            u'isbg - IMAP Spam Begone'
            >>> d = {'isbg': (u'IMAP',[b'Spam', r'Begone'])}
            >>> get_ascii_or_value(d)
            {u'isbg': (u'IMAP', [u'Spam', u'Begone'])}

        `Python3`:
            >>> get_ascii_or_value('isbg - IMAP Spam Begone')
            'isbg - IMAP Spam Begone'
            >>> d = {'isbg': (u'IMAP', [b'Spam', r'Begone'])}
            >>> get_ascii_or_value(d)
            {'isbg': ('IMAP', ['Spam', 'Begone'])}

    """
    def _get_ascii_or_value(val):
        """Try to convert to string.

        Args:
            val(str, byte): the value to convert.
        Returns:
            The value converted (or nor).

        """
        #: v2.0: In python3 we get the uids as binary, we try to normalized it
        #: to ascii or work as bytes.
        try:
            return val.decode('ascii')
        except UnicodeDecodeError:
            if python_version() > "3":
                return val
            else:
                try:
                    return val.decode(detect_enc(val)['encoding'])
                except (UnicodeDecodeError, TypeError):
                    return val

    if isinstance(value, bytes):
        return _get_ascii_or_value(value)

    if isinstance(value, (list, tuple)):
        lis = []
        for v in value:
            lis.append(get_ascii_or_value(v))
        if isinstance(value, tuple):
            lis = tuple(lis)
        return lis

    if isinstance(value, dict):
        dic = {}
        for k, v in value.items():
            dic[get_ascii_or_value(k)] = get_ascii_or_value(v)
        return dic

    return value


def popen(cmd):
    """Create a :py:class:`subprocess.Popen` instance.

    It calls `Popen(cmd, stdin=PIPE, stdout=PIPE, close_fds=True)`.

    Args:
        cmd (str): The command to use in the call to Popen.
    Returns:
        subprocess.Popen: The `Popen` object.

    """
    if os.name == 'nt':
        return Popen(cmd, stdin=PIPE, stdout=PIPE)
    return Popen(cmd, stdin=PIPE, stdout=PIPE, close_fds=True)


def score_from_mail(mail):
    """
    Search the spam score from a mail as a string.

    The returning format is ``d.d/d.d<br>`` and it contains the score found
    in the email.

    Args:
        mail (str): A email.message.Message decoded.
    Returns:
        str: The score found in the mail message.

    """
    res = re.search(r"score=(-?\d+(?:\.\d+)?) required=(\d+(?:\.\d+)?)", mail)
    score = res.group(1) + "/" + res.group(2) + "\n"
    return score


def shorten(inp, length):
    """Short a dict or a list a tuple or a string to a maximus length.

    Args:
        inp (dict, list, tuple, str): The object to short.
        length (int): The length.
    Returns:
        the shorted object.

    """
    if isinstance(inp, dict):
        return dict([(k, shorten(v, length)) for k, v in inp.items()])
    elif isinstance(inp, (list, tuple)):
        lis = [shorten(x, length) for x in inp]
        if isinstance(inp, tuple):
            lis = tuple(lis)
        return lis
    return truncate(inp, length)


def truncate(inp, length):
    u"""Truncate a string to a maximum length.

    Args:
        inp (str): The string to be shortened to his maximum length.
        length (int): The length.

    Returns:
        (str): the shorted string.

        It adds ``…`` at the end if it is shortened.

    Raises:
        ValueError: If length is low than 1.

    """
    if length < 1:
        raise ValueError("length should be 1 or greater")
    if len(inp) > length:
        return repr(inp)[:length - 1] + '…'
    return inp


class BraceMessage(object):
    """Comodity class to format a string.

    You can call it using: py: class: `~__`

    Example:
        >> > from isbg.utils import __
        >> > __("ffoo, boo {}".format(a))

    """

    def __init__(self, fmt, *args, **kwargs):
        """Initialize the object."""
        self.fmt = fmt        #: The string to be formated.
        self.args = args      #: The `*args`
        self.kwargs = kwargs  #: The `**kwargs**`

    def __str__(self):
        """Return the string formated."""
        return self.fmt.format(*self.args, **self.kwargs)

    def __repr__(self):
        """Return the representation formated."""
        return self.__str__()


__ = BraceMessage  # pylint: disable=invalid-name
