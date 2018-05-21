#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_imaputils.py
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

"""Test cases for isbg module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import email
import logging
import os
import sys
try:
    import pytest
except ImportError:
    pass

from socket import gaierror

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import imaputils  # noqa: E402


def test_mail_content():
    """Test mail_content function."""
    with pytest.raises(email.errors.MessageError,
                       message="mail 'None' is not a email.message.Message."):
        imaputils.mail_content(None)
    fmail = open('examples/spam.from.spamassassin.eml', 'rb')
    ftext = fmail.read()
    mail = imaputils.new_message(ftext)
    fmail.close()
    assert isinstance(imaputils.mail_content(mail), (str, bytes))


def test_new_message():
    """Test new_message function."""
    fmail = open('examples/spam.from.spamassassin.eml', 'rb')
    ftext = fmail.read()
    mail = imaputils.new_message(ftext)
    fmail.close()
    assert isinstance(mail, email.message.Message), \
        "%r is not a email.message.Message." % mail

    mail = imaputils.new_message("Foo")
    assert isinstance(mail, email.message.Message), \
        "%r is not a email.message.Message." % mail

    with pytest.raises((TypeError, AttributeError)):
        imaputils.new_message(None)
    with pytest.raises((TypeError, AttributeError)):
        imaputils.new_message(body="")
    with pytest.raises(TypeError, match="cannot be empty"):
        imaputils.new_message(body=b"")
    foo = imaputils.new_message(body=u"From:ñ@ñ.es")
    assert isinstance(foo, email.message.Message)


def test_get_message():
    """Test get_message."""
    # FIXME:
    pass


def test_imapflags():
    """Test imapflags."""
    assert imaputils.imapflags(['foo', 'boo']) == '(foo,boo)'


class TestIsbgImap4(object):
    """Test IsbgImap4."""

    def test(self):
        """Test the object."""
        with pytest.raises(gaierror, match="[Errno -5]",
                           message="No address associated with hostname"):
            imaputils.IsbgImap4()
        # FIXME: require network


def test_login_imap():
    """Test login_imap."""
    with pytest.raises(TypeError, match="ImapSettings",
                       message="spected a ImapSettings"):
        imaputils.login_imap(None)

    imapsets = imaputils.ImapSettings()
    imapsets.host = ''  # don't try to connect to internet
    imapsets.nossl = True
    with pytest.raises(Exception, match="[Errno -5]",
                       message="No address associated with hostname"):
        imaputils.login_imap(imapsets, logger=logging.getLogger(__name__))
    # FIXME: require network


class TestImapSettings(object):
    """Test object ImapSettings."""

    def test(self):
        """Test the object."""
        imapset = imaputils.ImapSettings()
        imaphash = imapset.hash
        assert imapset.hash == imaphash
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
        imapset.host = '127.0.0.1'
        assert imapset.hash.hexdigest() == 'ca057ebec07690c05f64959fff011c8d'
        assert imapset.hash.hexdigest() == 'ca057ebec07690c05f64959fff011c8d'
        assert imapset.hash.hexdigest() == 'ca057ebec07690c05f64959fff011c8d'
        imapset.host = 'localhost'
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
        assert imapset.hash.hexdigest() == '56fdd686137c8645d44024096a0ed441'
