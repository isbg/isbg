#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""isbg scans an IMAP Inbox and runs every entry against SpamAssassin.

For any entries that match, the message is copied to another folder,
and the original marked or deleted.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from .isbg import ISBG, ISBGError, __version__, __exitcodes__, __license__
from .spamproc import learn_mail, test_mail, feed_mail
from .sa_unwrap import unwrap

__all__ = ["__version__", "__exitcodes__", "__license__", "learn_mail",
           "test_mail", "feed_mail", "unwrap", "ISBG", "ISBGError"]
