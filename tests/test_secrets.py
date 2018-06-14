#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_spamaproc.py
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

"""Tests for secrets.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import os
import sys

try:
    import pytest
except ImportError:
    pass

# We add the upper dir to the path
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
from isbg import secrets      # noqa: E402
from isbg import imaputils    # noqa: E402

# To check if a cmd exists:

pytestmark = pytest.mark.xfail(reason="secrets.py needs to be re-written")

def cmd_exists(x):
    """Check for a os command line."""
    return any(os.access(os.path.join(path, x), os.X_OK)
               for path in os.environ["PATH"].split(os.pathsep))


def is_backend():
    """Get if the keyring backend is used."""
    return secrets.__use_secrets_backend__


def test_test():
    """Tests for learn_mail."""
    if is_backend():
        print("backend")
    else:
        print("not backend")


class Test_Secret(object):
    """Test secret class."""

    def test_hash2(self):
        """Test the hash."""
        imapset = imaputils.ImapSettings()
        sec = secrets.SecretIsbg(filename="", imapset=imapset)
        sec.hashlen == len(sec.hash)
        sec = secrets.SecretIsbg(filename="", imapset=imapset, hashlen=16)
        sec.hashlen == len(sec.hash)
        sec.hashlen == 16


class Test_SecretIsbg(object):
    """Test SecretIsbg class."""

    def test__obfuscate(self):
        """Test _obfuscate."""
        sec = secrets.SecretIsbg(filename="", imapset=imaputils.ImapSettings())
        # We construct a password:
        pas = sec._obfuscate(u"test")
        try:
            # pylint: disable=no-member
            pas = base64.encodebytes(bytes(pas, "utf-8"))   # py3
            pas = pas.decode("utf-8")
        except (TypeError, AttributeError):
            pas = base64.encodestring(pas)                  # py2
        res = """QVMVEGQ2ODYxMzdjODY0NWQ0NDAyNDA5NmEwZWQ0NDEwNjdlYmQxMTY0ZGUyMDliMWQ1ZjgzODMw
YzBjMDBlYWE3OWI1NzU1MzEzZmUzNmU3M2YzMGM5MmU1NmE2YjFlMDM0NTIxZTg1MWFlNzM0MTgy
NDQ5NDNlYWU1N2YwMzI0M2VhYTI0MTAyYTgwOWZkYjA5ZTBmZjkzM2UwYzIwZWI4YzhiZjZiMTRh
NTZlOTUwYjUyNjM5MzdhNTNjMWNmOWFjNGY3ODQyZDE4MWMxNWNkMDA0MjRkODZiNmQ4NzZjM2Ez
NTk2YTEyMDIyYTM4ZDc3YjM3Mzk2OGNlMzc1Yg==
"""
        assert pas == res, "Unexpected password encoded"

    def test__deobfuscate(self):
        """Test _deobfuscate."""
        sec = secrets.SecretIsbg(filename="", imapset=imaputils.ImapSettings())
        pas = """QVMVEGQ2ODYxMzdjODY0NWQ0NDAyNDA5NmEwZWQ0NDEwNjdlYmQxMTY0ZGUyMDliMWQ1ZjgzODMw
YzBjMDBlYWE3OWI1NzU1MzEzZmUzNmU3M2YzMGM5MmU1NmE2YjFlMDM0NTIxZTg1MWFlNzM0MTgy
NDQ5NDNlYWU1N2YwMzI0M2VhYTI0MTAyYTgwOWZkYjA5ZTBmZjkzM2UwYzIwZWI4YzhiZjZiMTRh
NTZlOTUwYjUyNjM5MzdhNTNjMWNmOWFjNGY3ODQyZDE4MWMxNWNkMDA0MjRkODZiNmQ4NzZjM2Ez
NTk2YTEyMDIyYTM4ZDc3YjM3Mzk2OGNlMzc1Yg==
"""
        pas = base64.b64decode(pas).decode("utf-8")
        ret = sec._deobfuscate(pas)
        assert ret == u"test"

    def test_get_and_set(self):
        """Test the get and set funcionts."""
        imapset = imaputils.ImapSettings()

        # Test with a erroneous filename.
        sec = secrets.SecretIsbg(filename="", imapset=imapset)
        assert sec.get("foo") is None
        with pytest.raises(EnvironmentError, match="\[Errno ",
                           message="A EnvironmentError should be raised."):
            sec.set("foo", "boo")

        # Test with a ok filename:
        sec = secrets.SecretIsbg(filename="tmp.txt", imapset=imapset)
        assert sec.get("foo") is None
        sec.set("foo1", "boo1")
        sec.set("foo2", "boo2")
        sec.set("foo3", "boo3")
        sec.set("foo3", "boo4")
        assert sec.get("foo3") == "boo4"

        with pytest.raises(ValueError, match="Key 'foo3' exists.",
                           message="It should raise a ValueError"):
            sec.set("foo3", "boo5", overwrite=False)

        assert sec.get("foo3") == "boo4"

        with pytest.raises(TypeError,
                           message="A TypeError should be raised."):
            sec.set("foo4", 4)
        assert sec.get("foo2") == "boo2"

        # Remove the created keys:
        sec.delete("foo1")
        assert sec.get("foo1") is None
        sec.delete("foo2")
        assert sec.get("foo2") is None

        # Remove non existant key:
        with pytest.raises(ValueError, match="Key 'foo4' not",
                           message="It should raise a ValueError"):
            sec.delete("foo4")

        # Remove last key, it should delete the file:
        sec.delete("foo3")
        assert sec.get("foo3") is None
        with pytest.raises(EnvironmentError, match="\[Errno 2\]",
                           message="A EnvironmentError should be raised."):
            os.remove("tmp.txt")

        # Remove non existant key in non existant file:
        with pytest.raises(ValueError, match="Key 'foo4' not",
                           message="It should raise a ValueError"):
            sec.delete("foo4")


class Test_SecretKeyring(object):
    """Test SecretKeyring class."""

    def test_get_and_set(self):
        """Test the get and set funcionts."""
        imapset = imaputils.ImapSettings()

        # Test:
        sec = secrets.SecretKeyring(imapset=imapset)
        assert sec.get("foo") is None
        sec.set("foo1", "boo1")
        sec.set("foo2", "boo2")
        sec.set("foo3", "boo3")
        sec.set("foo3", "boo4")
        assert sec.get("foo3") == "boo4"

        with pytest.raises(ValueError, match="Key 'foo3' exists.",
                           message="It should raise a ValueError"):
            sec.set("foo3", "boo5", overwrite=False)

        # Remove the created keys:
        sec.delete("foo1")
        assert sec.get("foo1") is None
        sec.delete("foo2")
        assert sec.get("foo2") is None

        # Remove non existant key:
        with pytest.raises(ValueError, match="Key 'foo4' not",
                           message="It should raise a ValueError"):
            sec.delete("foo4")

        sec.delete("foo3")
        assert sec.get("foo3") is None

        # Remove non existant key:
        with pytest.raises(ValueError, match="Key 'foo4' not",
                           message="It should raise a ValueError"):
            sec.delete("foo4")
