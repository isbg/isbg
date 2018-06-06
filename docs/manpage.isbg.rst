Manual page for isbg
====================

SYNOPSIS
--------

isbg **--imaphost** *<hostname>* **--imapuser** *<username>* [*options*]

isbg **--imaphost** *<hostname>* **--imapuser** *<username>* **--imaplist**
[*options*]

isbg (**-h** \| **--help**)

isbg **--usage**

isbg **--version**


DESCRIPTION
-----------

isbg scans an IMAP Inbox and runs every entry against SpamAssassin. For
any entries that match, the message is copied to another folder, and the
original marked or deleted.

Works with all common IMAP servers, can do IMAP over SSL, can remember
your password, will work painlessly against multiple IMAP accounts and
servers, is not involved in the mail delivery process, and so can run on
any machine that can contact your IMAP server and has the possibility to
skip spam detection to stick only to the teach feature.  


OPTIONS
-------

**--imaphost** *hostname*
    IMAP server name
**--imapuser** *username*
    Who you login as

**--imaplist**
    List imap directories

**-h**, **--help**
    Show the help screen
**--usage**
    Show usage information
**--version**
    Show version information

**--dryrun**
    Do not actually make any changes
**--delete**
    The spams will be marked for deletion from your inbox
**--deletehigherthan** *#*
    Delete any spam with a score higher than *#*
**--exitcodes**
    Use exitcodes to detail what happened
**--expunge**
    Cause marked for deletion messages to also be deleted (only useful
    if **--delete** is specified)
**--flag**
    The spams will be flagged in your inbox
**--gmail**
    Delete by copying to '*[Gmail]/Trash*' folder
**--ignorelockfile**
    Don't stop if lock file is present
**--imappasswd** *passwd*
    IMAP account password. This however is a really bad idea since any
    user on the system can run **ps** and see the command line arguments
**--imapport** *port*
    Use a custom port
**--imapinbox** *mbox*
    Name of your inbox folder [Default: *INBOX*]
**--learnspambox** *mbox*
    Name of your learn spam folder
**--learnhambox** *mbox*
    Name of your learn ham folder
**--learnthendestroy**
    Mark learnt messages for deletion
**--learnthenflag**
    Flag learnt messages
**--learnunflagfed**
    Only learn if unflagged (for **--learnthenflag**)
**--lockfilegrace**\ =<min>
    Set the lifetime of the lock file to [Default: *240.0*]
**--lockfilename** *file*
    Override the lock file name
**--maxsize** *numbytes*
    Messages larger than this will be ignored as they are unlikely to be
    spam
**--movehamto** *mbox*
    Move ham to folder
**--noninteractive**
    Prevent interactive requests
**--noreport**
    Don't include the SpamAssassin report in the message copied to your
    spam folder
**--nostats**
    Don't print stats
**--partialrun** *num*
    Stop operation after scanning '*num*' unseen emails [Default: *50*].
    You can run **isbg** without **--partialrun** with *--partialrun=0*
**--passwdfilename** *file*
    Use a file to supply the password
**--savepw**
    Store the password to be used in future runs. This will save the
    password in a file in your home directory. The file is named
    *.isbg-XXXX* where XXXX is a 16 byte identifier based on the IMAP
    host, username and port number (the same as for the multiple
    accounts description above). You can override the filename with
    **--passwdfilename**. The password is obfuscated, so anyone just
    looking at the contents won't be able to see what it is. However, if
    they study the code to isbg then they will be able to figure out how
    to de-obfuscate it, and recover the original password. (isbg needs
    the original password each time it is run as well). Consequently you
    should regard this as providing minimal protection if someone can
    read the file.
**--spamc**
    Use spamc instead of standalone SpamAssassin binary
**--spaminbox** *mbox*
    Name of your spam folder [Default: *INBOX.Spam*]
**--nossl**
    Don't use SSL to connect to the IMAP server
**--teachonly**
    Don't search spam, just learn from folders
**--trackfile** *file*
    Override the trackfile name
**--verbose**
    Show IMAP stuff happening
**--verbose-mails**
    Show mail bodies (extra-verbose)

(Your inbox will remain untouched unless you specify ``--flag`` or
``--delete``)


EXAMPLES
--------

Do your first run
~~~~~~~~~~~~~~~~~

    ``$ isbg --imaphost  mail.foo.com --imapuser rogerb@mail.foo.com --imaplist
    --savepw``

    ``IMAP password for rogerb@mail.foo.org@mail.foo.org:``

Will request the password for your user account and store it obfuscated for
future use, after login, it will show the IMAP folder list:

    *[u'  INBOX"', u'  INBOX.Esborranys"', u'  INBOX.Spam"', u'  INBOX.Sent"',
    u'  INBOX.NOSPAM"', u'  INBOX.Archive"', u'  INBOX.Drafts"',
    u'  INBOX.Trash"', u'  INBOX.Paperera"']*


Scan your account for spam
~~~~~~~~~~~~~~~~~~~~~~~~~~

In future uses you can scan for spam with:

    ``isbg --imaphost  mail.foo.com --imapuser rogerb@mail.foo.com``

After some time, it will return the stats:

    0 spams found in 0 messages

    0/0 was automatically deleted


OVERVIEW
--------

The amount of time it takes will be proportional to the size of your
inbox and the amount of mails specified with ``--partialrun``. You can specify
``--verbose`` if you want to see the gory details of what is going on.

You can now examine your spam folder and will see what spam was
detected. You can change the SpamAssassin threshold in your
*user\_prefs* file it created earlier.

isbg remembers which messages it has already seen, so that it doesn't
process them again every time it is run. If you are testing and do want
it to run again, then remove the trackfile (default
`$HOME/.cache/isbg/track\*`).

If you specified ``--savepw`` then isbg will remember your password the
next time you run against the same server with the same username. You
should not specify ``--savepw`` in future runs unless you want to change
the saved password.

You'll probably want something to actually be done with the original
spams in your inbox. By default nothing happens to them, but you have
two options available. If you specify ``--flag`` then spams will be
flagged.

You can get the messages marked for deletion by specifying ``--delete``.
If you never want to see them in your inbox, also specify the
``--expunge`` option after ``--delete`` and they will be removed when
isbg logs out of the IMAP server.  


SpamAssassin
~~~~~~~~~~~~

If you have never used SpamAssassin before, you'll probably be quite
nervous about it being too good and taking out legitimate email, or not
taking out enough spam. It has an easily adustable threshold to change
how aggressive it is. Run the following command to create your
preferences file (*$HOME/.spamassassin/user\_prefs*)::

    $ spamassassin </dev/null >/dev/null


Your Folder Names
~~~~~~~~~~~~~~~~~

Each IMAP implementation names their folders differently, and most IMAP clients
manage to hide most of this from you. If your IMAP server is *Courier*, then
your folders are all below INBOX, and use dots to separate the components.

The *UWash* server typically has the folders below Mail and uses slash (*/*) to
separate components.

If you don't know how your IMAP folders are implemented, you can always use the
``--imaplist`` option to find out.



SEE ALSO
--------

`spamassassin(1)`,
`Mail::SpamAssassin::Conf(3)`.

The full documentation for isbg is maintained in https://isbg.readthedocs.io/


EXIT CODES
----------

*0*
    All went well.
*10*
    There were errors in the command line arguments.
*11*
    The IMAP server reported an error or error with the IMAP connection.
*12*
    There was an error of communication between `spamc` or `SpamAssassin`.
*20*
    The program was not launched in an interactive terminal.
*30*
    Error with the *lock* file, is another instance of ``isbg`` must be
    running.
*-1*
    Other errors.

With ``--exitcodes`` there are also:

*1*
    There was at least one new message, and none of them were spam.
*2*
    There was at least one new message, and all them were spam.
*3*
    There were new messages, with at least one spam and one non-spam.


BUGS
----

You can report bugs on https://github.com/isbg/isbg/issues
