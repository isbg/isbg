#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  secrets.py
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

"""Imap secrets module for isbg - IMAP Spam Begone.

.. versionadded:: 2.1.0
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

try:
    import keyring              # noqa: F401
    import keyrings.alt.file    # noqa: F401
    __use_secrets_backend__ = True
except ImportError:
    __use_secrets_backend__ = False

import abc
import json
import logging
import os

from hashlib import md5

from isbg import utils
from .utils import __


class Secret(object):
    """Abstract class used to store secret info.

    Attributes:
        imapset (isbg.imaputils.ImapSettings): A imap setings object.
        hashlen (int): Length of the value hash. Must be a multiple of 16.
            Default 256.

    """

    __metaclass__ = abc.ABCMeta

    #: Logger object used to show debug info.
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())

    def __init__(self, imapset, hashlen=256):
        """Initialize a SecretKeyring object."""
        self.imapset = imapset
        self.hashlen = hashlen

        self._hashed_host = None
        self._hashed_user = None
        self._hashed_port = None
        self._hash = self.hash

    @property
    def hash(self):
        """Get the hash used to obfuscate the value/password."""
        if self._hashed_host != self.imapset.host or \
                self._hashed_user != self.imapset.user or \
                self._hashed_port != self.imapset.port:
            self._hashed_host = self.imapset.host
            self._hashed_user = self.imapset.user
            self._hashed_port = self.imapset.port
            self._hash = self._get_hash()
        return self._hash

    def _get_hash(self):
        # We make hash that the password is xor'ed against
        mdh = md5()
        mdh.update(self.imapset.host.encode())
        mdh.update(self.imapset.hash.digest())
        mdh.update(self.imapset.user.encode())
        mdh.update(self.imapset.hash.digest())
        mdh.update(repr(self.imapset.port).encode())
        mdh.update(self.imapset.hash.digest())
        the_hash = self.imapset.hash.hexdigest()
        while len(the_hash) < self.hashlen:
            self.imapset.hash.update(the_hash.encode())
            the_hash = the_hash + self.imapset.hash.hexdigest()
        return the_hash

    @abc.abstractmethod
    def get(self, key):
        """Get the value a key stored."""
        return None

    @abc.abstractmethod
    def set(self, key, value, overwrite=True):
        """Set a value of a key."""
        pass

    @abc.abstractmethod
    def delete(self, key):
        """Delete a stored key and his value."""
        pass


class SecretIsbg(Secret):
    """Class used to store secret info using our own implementation.

    Attributes:
        filename: the filename used to read or store the key and values.
        imapset (isbg.imaputils.ImapSettings): A imap setings object.
        hashlen (int, optional): Length of the value hash. Must be a multiple
            of 16. Defaults to 256.

    """

    def __init__(self, filename, imapset, hashlen=256):
        """Initialize a SecretISBG object."""
        self.filename = filename
        super(SecretIsbg, self).__init__(imapset, hashlen)
        self.logger.debug(
            "Initialized secret storage: {}".format(self.__class__.__name__))

    def _deobfuscate(self, value):
        """Deobfuscate value/password."""
        res = ""
        for i in range(0, self.hashlen):
            j = ord(value[i]) ^ ord(self.hash[i])
            if j == 0:
                break
            res = res + chr(j)
        return res

    def _obfuscate(self, value):
        """Obfuscate value/password."""
        if len(self.hash) > self.hashlen:
            raise ValueError(__(
                ("Password of length %d is too long to store " +
                 "(max accepted is %d)").format(len(self.hash), self.hashlen)))
        res = list(self.hash)
        for i, v in enumerate(value):
            res[i] = chr(ord(res[i]) ^ ord(v))
        return ''.join(res)

    @staticmethod
    def _store_data(filename, json_data):
        """Store json data into a file."""
        with open(filename, "w+") as json_file:
            os.chmod(filename, 0o600)
            json.dump(json_data, json_file)

    def get(self, key):
        """Get the value a key stored.

        Args:
            key(str): The key string requested.

        Returns:
            The value of the key or *None* if it cannot be found.

        """
        try:
            with open(self.filename, "r") as json_file:
                json_data = json.load(json_file)
        except EnvironmentError:
            json_data = {}

        if key in json_data:
            return json_data[key]
        else:
            return None

    def set(self, key, value, overwrite=True):
        """Set a value of a key.

        If it cannot find the file or their contents are not a right json data,
        it will overwrite it with the key and value pair.

        Args:
            key (str): The key to store.
            value (str): The value to store.
            overwrite (boolean, optional): If *True* it should overwrite and
                existing key. Defaults to *True*.

        Raises:
            EnvironmentError: If it cannot store the file.
            ValueError: If not overwrite and the key exists.

        """
        try:
            with open(self.filename) as json_file:
                json_data = json.load(json_file)
        except (EnvironmentError, ValueError):
            json_data = {}

        if key in json_data and not overwrite:
            raise ValueError("Key '%s' exists." % key)

        json_data[key] = value

        SecretIsbg._store_data(self.filename, json_data)

    def delete(self, key):
        """Delete a key.

        If no more keys are stored, it deletes the file.

        Args:
            key (str): The key to store.

        Raises:
            ValueError: If the key to delete is not found.

        """
        try:
            with open(self.filename) as json_file:
                json_data = json.load(json_file)
        except (EnvironmentError, ValueError):
            raise ValueError("Key '%s' not found and cannot be deleted." % key)

        try:
            del json_data[key]
        except (KeyError):
            raise ValueError("Key '%s' not found and cannot be deleted." % key)

        if not json_data:                 # Empty dict.
            os.remove(self.filename)      # Remove the file.
        else:
            SecretIsbg._store_data(self.filename, json_data)


class SecretKeyring(Secret):
    """Class used to store secrets using the *keyring* implementation.

    Attributes:
        imapset (isbg.imaputils.ImapSettings): A imap setings object.
        hashlen (int, optional): Length of the value hash. Must be a multiple
            of 16. Defaults to 256.
        keyring_backend: A keyring backend.

    """

    __SERVICE__ = 'isbg'

    def __init__(self, imapset, hashlen=256, keyring_backend=None):
        """Initialize a SecretKeyring object."""
        if keyring_backend:
            self.keyring_impl = keyring_backend
        else:
            self.keyring_impl = keyring.get_keyring()
        super(SecretKeyring, self).__init__(imapset, hashlen)
        self.logger.debug(
            "Initialized secret storage {} using keyring storage {}".format(
                self.__class__.__name__, self.keyring_impl.__class__.__name__))

    def get(self, key):
        """Get the value a key stored.

        Args:
            key(str): The key string requested.

        Returns:
            The value of the key or *None* if it cannot be found.

        """
        return self.keyring_impl.get_password(self.__SERVICE__,
                                              self.hash + "-" + key)

    def set(self, key, value, overwrite=True):
        """Set a value of a key.

        If it cannot find the file or their contents are not a right json data,
        it will overwrite it with the key and value pair.

        Args:
            key (str): The key to store.
            value (str): The value to store.
            overwrite (boolean, optional): If *True* it should overwrite and
                existing key. Defaults to *True*.

        Raises:
            ValueError: If overwrite is *False* and the key exists.

        """
        if not overwrite and self.get(key):
            raise ValueError("Key '%s' exists." % key)

        self.keyring_impl.set_password(self.__SERVICE__,
                                       self.hash + '-' + key, value)

    def delete(self, key):
        """Delete the first occurrence of the key.

        Args:
            key (str): The key to store.

        Raises:
            ValueError: If the key to delete is not found.

        """
        try:
            self.keyring_impl.delete_password(self.__SERVICE__,
                                              self.hash + '-' + key)
        except (keyring.errors.PasswordDeleteError):
            raise ValueError("Key '%s' not found and cannot be deleted." % key)
