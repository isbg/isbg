IMAP Spam Begone
================

**isbg** is a script and a python module that makes it easy to scan an
IMAP inbox for spam using *SpamAssassin* and get your spam moved to another
folder.

Unlike the normal mode of deployments for *SpamAssassin*, isbg does not need to
be involved in mail delivery, and can run on completely different machines to
where your mailbox actually is. So this is the perfect tool to take good care
of your ISP mailbox without having to leave it.

You can read the full documentation in `Read the docs`_.

.. _Read the docs: https://isbg.readthedocs.io/

.. contents:: Table of Contents
   :depth: 3

Features
--------

-  Works with all common IMAP servers
-  Works on Linux, MacOS X and Windows (even smartphones!)
-  Can do IMAP over SSL
-  Can remember your password
-  Will work painlessly against multiple IMAP accounts and servers
-  Is not involved in the mail delivery process, and so can run on any
   machine
   that can contact your IMAP server
-  Highly configurable
-  Sensible defaults so you don't have to do any configuring :-)
-  Possibility to skip spam detection to stick only to the teach feature
-  Don't fail when meeting horrible and bad formed mail
-  Lock file to prevent multiple instance to run at the same time (for
   cron jobs)


Installation
------------

**isbg** install a python package module and also a script to use it ``isbg``,
it also install another script to unwrap messages: ``isbg_sa_unwrap``.

Dependencies
~~~~~~~~~~~~

**isbg** is written in the Python language. Python is installed by default on
most Linux systems. You can can find out more about Python at
`Python home page`_.

Make sure you have *SpamAssassin* installed. All the necessary information
can be found on the `SpamAssassin wiki`_. *SpamAssassin* should be on your
``$PATH`` (it installs in ``/usr/bin/`` by default)

To run, ``isbg`` also depends on some python modules.

- `docopt`_ for command line options.

- `cchardet`_ or `chardet`_  for encoding detection.

- `xdg`_ to found the ``.cache`` directory. ``xdg`` is not required, if it's
  not installed, **isbg** will try to found ``.cache``.

.. _Python home page: https://www.python.org/
.. _SpamAssassin wiki: https://wiki.apache.org/spamassassin/FrontPage
.. _docopt: https://pypi.python.org/pypi/docopt
.. _cchardet: https://pypi.python.org/pypi/cchardet
.. _chardet: https://pypi.python.org/pypi/chardet
.. _xdg: https://pypi.python.org/pypi/xdg


Install from source
~~~~~~~~~~~~~~~~~~~

From the main directory where you have download isbg, run::

    $ python setup.py install --record installed_files.txt

It will install under ``/usr/local/``. In ``installed_files.txt`` there should
be the list of files installed. To uninstall them, use::

    $ tr '\n' '\0' < installed_files.txt | xargs -0 rm -vf --

In windows systems, you can build a windows installer using::

    $ python setup.py bdist_wininst


install with PyPi
~~~~~~~~~~~~~~~~~

You also can install **isbg** from `Pypi`_::

    $ pip install isbg

To see the files installed you can use::

    $ pip show isbg --files

And to uninstall it::

    $ pip uninstall isbg

.. _Pypi: https://pypi.python.org/pypi/isbg


Usage
-----

SpamAssassin
~~~~~~~~~~~~

If you have never used *SpamAssassin* before, you'll probably be quite
nervous about it being too good and taking out legitimate email, or not
taking out enough spam. It has an easily adjustable threshold to change
how aggressive it is. Run the following command to create your
preferences file::

    $ spamassassin  </dev/null >/dev/null
    Created user preferences file: /home/rogerb/.spamassassin/user_prefs

You can then edit ``$HOME/.spamassassin/user_prefs`` and change the
thresholds.

You can also edit the system-wide settings in
``/etc/spamassassin/locals.cf``.

If you want to use the ``--learnspambox`` or ``--learnhambox``, you'll have
to configure your spamassassin.


Configure your spamassassin
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to use ``--learnspambox`` or ``--learnhambox`` features,
you have to add this configuration:


Allow Tell
''''''''''

You have to start ``spamd`` with the ``--allow-tell`` option.

On Debian systems (Debian and Ubuntu), you have to edit
``/etc/default/spamassassin`` and replace::

    OPTIONS="-D --create-prefs --max-children 5 --helper-home-dir"

by::

    OPTIONS="-D --allow-tell --create-prefs --max-children 5 \
    --helper-home-dir"

Don't forget to restart your ``spamd`` server after that (``sudo service
spamassassin restart`` on *Debian*).


CLI Options
~~~~~~~~~~~

The default behavior of **isbg** is to not make any changes your Inbox
unless you specify specific command line options. Consequently you can
experiment without worry at the beginning.

Your first step is to create a new folder to receive suspected spam.
I use one named 'spam'.

Run isbg with the ``--help`` option to see what options are available or check
its manual page with ``$ man isbg`` [#]_.

You can also unwrap *SpamAssassin* bundled emails with ``isbg_sa_unwrap``,
you can use the ``--help`` option to check the available options or
``$ man isbg_sa_unwrap`` to check its manual page [#]_.

.. [#] You can see it in :doc:`manpage.isbg` page or if you are reading this
   from `github manpage.isbg doc`__

.. [#] You can see it in :doc:`manpage.isbg_sa_unwrap` page or if you are
   reading this from `github manpage.isbg_sa_unwrap doc`__

.. __: docs/manpage.isbg.rst

.. __: docs/manpage.isbg_sa_unwrap.rst


How does it work?
~~~~~~~~~~~~~~~~~

IMAP assigns each message in a folder a unique id. **isbg** scans the
folder for messages it hasn't seen before, and for each one, downloads
the message and feeds it to *SpamAssassin*. If *SpamAssassin* says the
message is spam, then the *SpamAssassin* report is uploaded into your spam
folder. Unless you specify the ``--noreport`` option, in which case the
message is copied from your Inbox to the Spam folder (the copy happens on
the IMAP server itself so this option is good if you are on a low
bandwidth connection).


Multiple accounts
~~~~~~~~~~~~~~~~~

By default **isbg** saves the list of seen IMAP message unique IDs in a
file in your home directory. It is named ``.isbg-trackXXXX`` where XXXX is a
16 byte identifier based on the IMAP host, username and port number.
Consequently you can just run **isbg** against different servers/accounts
and it will automatically keep the tracked UIDs separate. You can
override the filename with ``--trackfile``.

To run **isbg** for multiple accounts one after another, it is possible to use
bash scripts like the ones in the folder "bash\_scripts". Since these scripts
contain passwords and are thus sensitive data, make sure the file permissions
are very restrictive.


Saving your password
~~~~~~~~~~~~~~~~~~~~

If you don't want **isbg** to prompt you for your password each time,
you can specify the ``--savepw`` option. This will save the password in a
file in your home directory. The file is named ``$HOME/.cache/isbg/.isbg-XXXX``
where XXXX is a 16 byte identifier based on the IMAP host, username and port
number (the same as for the multiple accounts description above). You can
override the filename with ``--passwdfilename``.

The password is obfuscated, so anyone just looking at the contents
won't be able to see what it is. However, if they study the code to isbg
then they will be able to figure out how to de-obfuscate it, and
recover the original password. (**isbg** needs the original password each
time it is run as well).

Consequently you should regard this as providing minimal protection if
someone can read the file.


SSL
~~~

**isbg** can do IMAP over SSL if your version of Python has been
compiled with SSL support. Since Python 2.6, SSL comes built in with Python.

However you should be aware that the SSL support does NOT check the
certificate name nor validate the issuer. If an attacker can intercept
the connection and modify all the packets flowing by, then they will be
able to pose as the IMAP server. Other than that, the connection will
have the usual security features of SSL.


Read and Seen flags
~~~~~~~~~~~~~~~~~~~

There are two flags IMAP uses to mark messages, ``Recent`` and ``Seen``.
``Recent`` is sent to the first IMAP client that connects after a new
message is received. Other clients or subsequent connections won't see
that flag. The ``Seen`` flag is used to mark a message as read. IMAP clients
explicitly set ``Seen`` when a message is being read.

Pine and some other mailers use the ``Recent`` flag to mark new mail.
Unfortunately this means that if isbg or any other IMAP client has even
looked at the Inbox, the messages won't be shown as new. It really
should be using ``Seen``.

The IMAP specification does not permit clients to change the ``Recent``
flag.

Gmail Integration
~~~~~~~~~~~~~~~~~

*Gmail* has a few unique ways that they interact with a mail client. **isbg**
must be considered to be a client due to interacting with the Gmail servers
over IMAP, and thus, should conform to these special requirements for proper
integration.

There are two types of deletion on a *Gmail* server.

- **Type 1:** Move a message to '[Gmail]/Trash' folder.

  This "removes all labels" from the message. It will no longer appear in any
  folders and there will be a single copy located in the trash folder.
  Gmail will "empty the trash" after the received email message is 30 days old.

  You can also do a "Normal IMAP delete" on the message in the trash
  folder to cause it to be removed permanently without waiting 30 days.

- **Type 2:** Normal IMAP delete flag applied to a message.

  This will "remove a single label" from a message. It will no longer appear
  in the folder it was removed from but will remain in other folders and also
  in the "All Mail" folder.

  Enable Gmail integration mode by passing ``--gmail`` in conjunction with
  ``--delete`` on the command line when invoking isbg. These are the features
  which are tweaked:

  - The ``--delete`` command line switch will be modified so that it
    will result in a Type 1 delete.

  - The ``--deletehigherthan`` command line switch will be modified so
    that it will results in a Type 1 delete.

  - If ``--learnspambox`` is used along with the ``--learnthendestroy``
    option, then a Type 1 delete occurs leaving only a copy of the spam in the
    Trash.

  - If ``--learnhambox`` is used along with the ``--learnthendestroy``
    option, then a Type 2 delete occurs, only removing the single label.

Reference information was taken from `gmail IMAP usage`_.

.. _gmail IMAP usage: https://support.google.com/mail/answer/78755?hl=en


Ignored emails
~~~~~~~~~~~~~~

By default, **isbg** ignores emails that are bigger than 120,000 bytes since
spam are not often that big. If you ever get emails with score of 0 on 5
(0.0/5.0), it is likely that *SpamAssassin* is skipping it due to size.

Defaut maximum size can be changed with the use of the ``--maxsize``
option.


Partial runs
~~~~~~~~~~~~

By default, **isbg** scans 50 emails for operation: spam learn, ham learn and
spam detection. If you want to change the default, you can use the
``--partialrun`` option specifying the number. **isbg** tries to read first the
new messages and tracks the before seen to not reprocess them.

This is useful when your inbox has a lot of emails, since deletion and mail
tracking are only performed at the end of the run and full scans can take too
long.

If you want that isbg does track all the emails you can disable the
``partialrun`` with ``--partialrun=0``.


Contact and about
-----------------

Please join our `isbg mailing list`_ if you use **isbg** or contribute to
it! The mailing list will be used to announce project news and to discuss
the further developement of **isbg**.

You can also hang out with us on IRC, at ``#isbg`` on Freenode.

See the CONTRIBUTORS file in the git repository for more information on who
wrote and maintains this software.

.. _isbg mailing list: https://mail.python.org/mm3/mailman3/lists/isbg.python.org/


License
-------

This program is licensed under the `GNU General Public License version
3`_.

This is free software: you are free to change and redistribute it. There is
NO WARRANTY, to the extent permitted by law.

.. _GNU General Public License version 3: https://www.gnu.org/licenses/gpl-3.0.txt
