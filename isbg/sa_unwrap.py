#!/usr/bin/python
# -*- coding: utf-8 -*-

r"""
Parse an *rfc2822* email message and unwrap it if contains spam attached.

To know it it checks for an x-spam-type=original payload.

Works on python 2.7+ and 3.x (uses some fairly ugly hacks to do so)

Does not perfectly preserve whitespace (esp. \r\n vs. \n and \t vs space), also
does that differently between python 2 and python 3, but this should not impact
spam-learning purposes.

Examples:
    It will return the original mail into a spamassassin mail:
        >>> import isbg.sa_unwrap
        >>> f = open('examples/spam.from.spamassassin.eml','rb')
        >>> spams = isbg.sa_unwrap.unwrap(f)
        >>> f.close()
        >>> for spam in spams:
        >>>     print(spam)

    or::

        $ isbg_sa_unwrap.py < examples/spam.from.spamassassin.eml
        $ isbg_sa_unwrap.py < examples/spam.eml

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function  # Now we can use print(...
from __future__ import unicode_literals

import email
import email.message
from io import IOBase
import os
import sys

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __sa_unwrap__.py
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))
import isbg  # noqa: E402

try:
    # Creating command-line interface
    from docopt import docopt, DocoptExit, printable_usage
except ImportError:
    sys.stderr.write("Missing dependency: docopt\n")
    raise

# works with python 2 and 3
try:
    FILE_TYPES = (file, IOBase)  #: The `stdin` is also a file.
except NameError:
    FILE_TYPES = (IOBase,)  # Python 3

try:
    PARSE_FILE = email.message_from_binary_file  # Python3
    MESSAGE = email.message_from_bytes           # Python3
except AttributeError:
    PARSE_FILE = email.message_from_file         # Python2
    MESSAGE = email.message_from_string          # Python2+3


def sa_unwrap_from_email(msg):
    """Unwrap a email from the spamassasin email.

    Args:
        msg (email.message.Message): email to unwrap.

    Returns:
        [email.message.Message]: A list with the unwraped mails.

    """
    if msg.is_multipart():
        parts = []
        ploads = msg.get_payload()
        for pload in ploads:
            if pload.get_param('x-spam-type', '') == 'original':
                # We remove the headers added by spamassassin:
                if hasattr(pload, 'as_bytes'):
                    pl_bytes = pload.as_bytes()
                else:
                    pl_bytes = pload.as_string()
                el_idx = pl_bytes.index(b'\n\n')
                parts.append(MESSAGE(pl_bytes[el_idx + 2:]))
        if parts:  # len(parts) > 0
            return parts
    return None


def unwrap(mail):
    """Unwrap a email from the spamassasin email.

    the mail could be a email.message.Email, a file or a string or buffer.
    It ruturns a list with all the email.message.Email founds.

    Args:
        mail (email.message.Message, FILE_TYPES, str): the mail to unwrap.

    Returns:
        [email.message.Message]: A list with the unwraped mails.

    """
    if isinstance(mail, email.message.Message):
        return sa_unwrap_from_email(mail)
    if isinstance(mail, FILE_TYPES):  # files are also stdin...
        return sa_unwrap_from_email(PARSE_FILE(mail))
    try:
        mail = email.message_from_bytes(mail)  # py3 only
    except AttributeError:
        mail = email.message_from_string(mail)
    return sa_unwrap_from_email(mail)


def __isbg_sa_unwrap_opts__():  # noqa: D207
    """isbg-sa-unwrap.py unwrap a mail bundled by SpamAssassin.

it parses a rfc2822 email message and unwrap it if contains spam attached.

Command line Options::

 Usage:
  isbg_sa_unwrap.py [--from <FROM_FILE>] [--to <TO_FILE>]
  isbg_sa_unwrap.py (-h | --help)
  isbg_sa_unwrap.py --usage
  isbg_sa_unwrap.py --version

 Options:
  -h, --help    Show the help screen.
  --usage       Show the usage information.
  --version     Show the version information.

  -f FILE, --from=FILE  Filename of the email to read and unwrap. If not
                        informed, the stdin will be used.
  -t FILE, --to=FILE    Filename to write the unwrapped  email. If not
                        informed, the stdout will be used.

"""


def isbg_sa_unwrap():
    """Run when this module is called from the command line."""
    try:
        opts = docopt(__isbg_sa_unwrap_opts__.__doc__,
                      version="isbg_sa_unwrap v" + isbg.__version__ +
                      ", from: " + os.path.abspath(__file__) + "\n\n" +
                      isbg.__license__)
    except DocoptExit:
        sys.stderr.write('Error with options!!!\n')
        raise

    if opts.get("--usage"):
        sys.stdout.write(
            "{}\n".format(printable_usage(__isbg_sa_unwrap_opts__.__doc__)))
        return

    if opts.get("--from"):
        file_in = open(opts["--from"], 'rb')
    else:
        file_in = sys.stdin

    if hasattr(file_in, 'buffer'):
        # select byte streams if they exist (on python 3)
        file_in = file_in.buffer    # pylint: disable=no-member

    spams = unwrap(file_in.read())
    file_in.close()

    if spams is None:
        sys.stderr.write("No spam into the mail detected.\n")
        return

    if opts.get("--to"):
        file_out = open(opts["--to"], 'wb')
    else:
        file_out = sys.stdout

    for spam in spams:
        file_out.write(spam.as_string())

    if file_out != sys.stdout:
        file_out.close()


if __name__ == '__main__':
    isbg_sa_unwrap()
