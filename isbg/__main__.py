#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  __main__.py
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

"""isbg scans an IMAP Inbox and runs every entry against SpamAssassin.

See Also:
    :py:mod:`isbg` for instance creation.

.. versionchanged:: 2.0
    ``--partialrun`` defaults to 50. Use ``--partialrun=0`` to run without
    partial run.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

try:
    # Creating command-line interface
    from docopt import docopt, DocoptExit, printable_usage
except ImportError:
    sys.stderr.write("Missing dependency: docopt\n")
    raise

if __package__ is None and not hasattr(sys, 'frozen'):
    # direct call of __main__.py
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))
from isbg import isbg  # noqa: E402


def __cmd_opts__():  # noqa: D207
    """Isbg scans an IMAP Inbox and runs every entry against SpamAssassin.

Command line Options::

 Usage:
  isbg.py --imaphost <hostname> --imapuser <username> [options]
  isbg.py --imaphost <hostname> --imapuser <username> --imaplist [options]
  isbg.py (-h | --help)
  isbg.py --usage
  isbg.py --version

 Options:
  --imaphost hostname    IMAP server name.
  --imapuser username    Who you login as.

  --imaplist             List imap directories.

  -h, --help             Show the help screen.
  --usage                Show the usage information.
  --version              Show the version information.

  --dryrun               Do not actually make any changes.
  --delete               The spams will be marked for deletion from
                         your inbox.
  --deletehigherthan #   Delete any spam with a score higher than #.
  --exitcodes            Use exitcodes to detail  what happened.
  --expunge              Cause marked for deletion messages to also be
                         deleted (only useful if --delete is
                         specified).
  --flag                 The spams will be flagged in your inbox.
  --gmail                Delete by copying to '[Gmail]/Trash' folder.
  --ignorelockfile       Don't stop if lock file is present.
  --imappasswd passwd    IMAP account password.
  --imapport port        Use a custom port.
  --imapinbox mbox       Name of your inbox folder [Default: INBOX].
  --learnspambox mbox    Name of your learn spam folder.
  --learnhambox mbox     Name of your learn ham folder.
  --learnthendestroy     Mark learnt messages for deletion.
  --learnthenflag        Flag learnt messages.
  --learnunflagged       Only learn if unflagged
                         (for  --learnthenflag).
  --learnflagged         Only learn flagged.
  --lockfilegrace=<min>  Set the lifetime of the lock file
                         [default: 240.0].
  --lockfilename file    Override the lock file name.
  --maxsize numbytes     Messages larger than this will be ignored as
                         they are unlikely to be spam.
  --movehamto mbox       Move ham to folder.
  --noninteractive       Prevent interactive requests.
  --noreport             Don't include the SpamAssassin report in the
                         message copied to your spam folder.
  --nostats              Don't print stats.
  --partialrun num       Stop operation after scanning 'num' unseen
                         emails. Use 0 to run without partial run
                         [default: 50].
  --passwdfilename fn    Use a file to supply the password.
  --savepw               Store the password to be used in future runs.
  --spamc                Use spamc instead of standalone SpamAssassin
                         binary.
  --spaminbox mbox       Name of your spam folder
                         [Default: INBOX.Spam].
  --nossl                Don't use SSL to connect to the IMAP server.
  --teachonly            Don't search spam, just learn from folders.
  --trackfile file       Override the trackfile name.
  --verbose              Show IMAP stuff happening.
  --verbose-mails        Show mail bodies (extra-verbose).

  (Your inbox will remain untouched unless you specify --flag or
   --delete)
    """


def parse_args(sbg):
    """Argument processing of the command line.

    :param sbg: the `isbg.ISBG` instance which would be updated with the
                parameters.
    :type sbg: isbg.ISBG
    :return: `None`

    :Example: You can run it using:

        >>> sbg = isbg.ISBG()
        >>> parse_args(sbg)
    """
    try:
        opts = docopt(__cmd_opts__.__doc__, version="isbg_v" +
                      isbg.__version__ + ", from: " +
                      os.path.abspath(__file__) + "\n\n" + isbg.__license__)
        opts = dict([(k, v) for k, v in opts.items()
                     if v is not None])
    except DocoptExit as exc:
        raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                             "Option processing failed - " + str(exc))

    if opts.get("--usage"):
        print(printable_usage(__cmd_opts__.__doc__))
        return 1

    if opts.get("--deletehigherthan") is not None:
        try:
            sbg.deletehigherthan = float(opts["--deletehigherthan"])
        except Exception:  # pylint: disable=broad-except
            raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                                 "Unrecognized score - " +
                                 opts["--deletehigherthan"])
        if sbg.deletehigherthan < 1:
            raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                                 "Score " + repr(sbg.deletehigherthan) +
                                 " is too small")

    if opts["--flag"] is True:
        sbg.spamflags.append("\\Flagged")

    sbg.imapsets.host = opts.get('--imaphost', sbg.imapsets.host)
    sbg.imapsets.passwd = opts.get('--imappasswd',
                                   sbg.imapsets.passwd)
    sbg.imapsets.port = opts.get('--imapport', sbg.imapsets.port)
    sbg.imapsets.user = opts.get('--imapuser', sbg.imapsets.user)
    sbg.imapsets.inbox = opts.get('--imapinbox', sbg.imapsets.inbox)
    sbg.imapsets.spaminbox = opts.get('--spaminbox', sbg.imapsets.spaminbox)
    sbg.imapsets.learnspambox = opts.get('--learnspambox')
    sbg.imapsets.learnhambox = opts.get('--learnhambox')
    sbg.imapsets.nossl = opts.get('--nossl', sbg.imapsets.nossl)

    sbg.lockfilegrace = float(opts.get('--lockfilegrace', sbg.lockfilegrace))

    sbg.nostats = opts.get('--nostats', False)
    sbg.dryrun = opts.get('--dryrun', False)
    sbg.delete = opts.get('--delete', False)
    sbg.gmail = opts.get('--gmail', False)

    if opts.get("--maxsize") is not None:
        try:
            sbg.maxsize = int(opts["--maxsize"])
        except (TypeError, ValueError):
            raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                                 "Unrecognised size - " + opts["--maxsize"])
        if sbg.maxsize < 1:
            raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                                 "Size " + repr(sbg.maxsize) + " is too small")

    sbg.movehamto = opts.get('--movehamto')

    if opts["--noninteractive"] is True:
        sbg.interactive = 0

    sbg.noreport = opts.get('--noreport', sbg.noreport)

    sbg.lockfilename = opts.get('--lockfilename', sbg.lockfilename)

    sbg.trackfile = opts.get('--trackfile', sbg.trackfile)

    sbg.partialrun = opts.get('--partialrun', sbg.partialrun)
    try:
        sbg.partialrun = int(opts["--partialrun"])
    except ValueError:
        raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                             "partialrun \'{}\' must be a integer".format(
                             repr(sbg.partialrun)))
    if sbg.partialrun < 0:
        raise isbg.ISBGError(isbg.__exitcodes__['flags'],
                             ("Partial run \'{}\' number must be equal to " +
                              "0 or higher").format(repr(sbg.partialrun)))
    elif sbg.partialrun == 0:
        sbg.partialrun = None

    sbg.verbose = opts.get('--verbose', sbg.verbose)
    sbg.verbose_mails = opts.get('--verbose-mails', sbg.verbose_mails)
    sbg.ignorelockfile = opts.get("--ignorelockfile", sbg.ignorelockfile)
    sbg.savepw = opts.get('--savepw', sbg.savepw)
    sbg.passwdfilename = opts.get('--passwdfilename', sbg.passwdfilename)

    sbg.imaplist = opts.get('--imaplist', sbg.imaplist)

    sbg.learnunflagged = opts.get('--learnunflagged', sbg.learnunflagged)
    sbg.learnflagged = opts.get('--learnflagged', sbg.learnflagged)
    sbg.learnthendestroy = opts.get('--learnthendestroy', sbg.learnthendestroy)
    sbg.learnthenflag = opts.get('--learnthendestroy', sbg.learnthenflag)
    sbg.expunge = opts.get('--expunge', sbg.expunge)

    sbg.teachonly = opts.get('--teachonly', sbg.teachonly)
    sbg.spamc = opts.get('--spamc', sbg.spamc)

    sbg.exitcodes = opts.get('--exitcodes', sbg.exitcodes)

    # fixup any arguments
    if opts.get("--imapport") is None:
        if opts["--nossl"] is True:
            sbg.imapsets.port = 143
        else:
            sbg.imapsets.port = 993


def main():
    """Run when this module is called from the command line.

    When the main function ends, it throw a sys.exit with 0 if it has end ok
    or one of the :py:data:`isbg.isbg.__exitcodes__`
    """
    sbg = isbg.ISBG()
    try:
        if parse_args(sbg) == 1:  # usage option
            sys.exit(0)
        return sbg.do_isbg()  # return the exit code.
    except isbg.ISBGError as err:
        sys.stderr.write(err.message)
        sys.stderr.write("\nUse --help to see valid options and arguments\n")
        if err.exitcode == -1:
            raise
        sys.exit(err.exitcode)


if __name__ == '__main__':
    isbgret = main()  # pylint: disable=invalid-name
    if isbgret is not None:
        sys.exit(isbgret)
