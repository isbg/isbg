#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_utils.py
#  This file is part of utils.
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

"""Test cases for utils module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

try:
    import pytest
except ImportError:
    pass

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import utils  # noqa: E402


def test_detect_enc():
    """Test the detenct_enc function."""
    assert 'encoding' in utils.detect_enc(b"foo")
    assert 'encoding' in utils.detect_enc(b"")


def test_hexof_dehexof():
    """Test the dehexof function."""
    dehex = utils.dehexof("50402A")
    assert dehex == "P@*"
    assert utils.hexof(dehex) == "50402a"
    with pytest.raises(ValueError,
                       match=repr("G") + " is not a valid hexadecimal digit",
                       message="Not error or unexpected error message"):
        utils.dehexof("G")
    dehex = utils.dehexof("50402a")
    assert dehex == "P@*"
    assert utils.hexof(dehex) == "50402a"


def test_get_ascii_or_value():
    """Test get_ascii_or_value."""
    ret = utils.get_ascii_or_value(b'IMAP Spam Begone')
    assert ret == u'IMAP Spam Begone', 'should return IMAP Spam Begone'
    ret = utils.get_ascii_or_value(u'IMAP Spam Begone')
    assert ret == u'IMAP Spam Begone', 'should return IMAP Spam Begone'
    ret = utils.get_ascii_or_value('IMAP Spam Begone')
    assert ret == u'IMAP Spam Begone', 'should return IMAP Spam Begone'
    ret = utils.get_ascii_or_value(22)
    assert ret == 22, 'should return 22 (int)'

    d = {'isbg': (u'IMAP', [b'Spam', r'Begone'])}
    ret = utils.get_ascii_or_value(d)
    assert ret == {u'isbg': (u'IMAP', [u'Spam', u'Begone'])}, 'error'


def test_score_from_mail():
    """Test score_from_mail."""
    # Without score:
    fmail = open('examples/spam.eml', 'rb')
    ftext = fmail.read()
    fmail.close()
    with pytest.raises(AttributeError, message="Should rise AttributeError."):
        ret = utils.score_from_mail(ftext.decode(errors='ignore'))
    # With score:
    fmail = open('examples/spam.from.spamassassin.eml', 'rb')
    ftext = fmail.read()
    fmail.close()
    ret = utils.score_from_mail(ftext.decode(errors='ignore'))
    assert ret == u"6.4/5.0\n", "Unexpected score."


def test_shorten():
    """Test the shorten function."""
    # We try with dicts:
    dic = {1: 'Option 1', 2: u'Option 2', 3: b'Option 3'}
    assert dic == utils.shorten(dic, 8), "The dicts should be the same."
    dic2 = utils.shorten(dic, 7)
    assert dic != dic2, "The dicts should be diferents."
    # Note: py2 and py3:
    assert dic2[1] in ['u\'Opti…', '\'Optio…'], "Unexpected shortened string."
    assert dic2[2] in ['u\'Opti…', '\'Optio…'], "Unexpected shortened string."
    assert dic2[3] in ['\'Optio…', 'b\'Opti…'], "Unexpected shortened string."

    # We try with lists:
    ls = ['Option 1', 'Option 2', 'Option 3']
    assert ls == utils.shorten(ls, 8)
    ls2 = utils.shorten(ls, 7)
    for k in ls2:
        assert k in ['u\'Opti…', '\'Optio…'], "Unexpected shortened string."

    # We try with strings:
    assert "Option 1" == utils.shorten("Option 1", 8), \
        "Strings should be the same."
    assert utils.shorten("Option 1", 7) in ['u\'Opti…', "\'Optio…"], \
        "Strings should be diferents."

    # Others:
    with pytest.raises(TypeError, message="None should raise a TypeError."):
        utils.shorten(None, 8)
    with pytest.raises(TypeError, message="None should raise a TypeError."):
        utils.shorten(None, 7)
    with pytest.raises(TypeError, message="None should raise a TypeError."):
        utils.shorten(False, 8)
    with pytest.raises(TypeError, message="None should raise a TypeError."):
        utils.shorten(True, 7)
    with pytest.raises(TypeError, message="int should raise a TypeError."):
        utils.shorten(1, 7)
    with pytest.raises(TypeError, message="float should raise a TypeError."):
        utils.shorten(1.0, 7)
    with pytest.raises(ValueError, message="length should be at least 1."):
        utils.shorten("123", 0)
    with pytest.raises(TypeError, message="int should be not supported."):
        assert utils.shorten([1, 2, 3], 2)
    assert utils.shorten(["111", "2", "3"], 3) == ["111", "2", "3"]
    assert utils.shorten(("111", "2", "3"), 3) == ("111", "2", "3")


def test_BraceMessage():
    """Test BraceMessage."""
    ret = utils.BraceMessage("Test {} {}".format(1, "is one."))
    assert str(ret) == "Test 1 is one."
    ret = utils.__("Test {} {}".format(1, "is one."))
    assert str(ret) == "Test 1 is one."
