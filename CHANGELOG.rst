Changelog
=========

What has been done since last release.

Unreleased
----------

* run spamassassin only once per mail check (thanks to rsmuc)

isbg 2.1.3 (20181024)
--------------------

* don't build the documentation during the install
* fix pip builds

isbg 2.1.2 (20180917)
---------------------

* fix a bug with the interaction between --learnspambox and --dryrun
* remove mention of Python 2 in the docs

isbg 2.1.1 (201808729)
----------------------

* Fix documentation
* Update setup.py in order to upload to PyPi

isbg 2.1.0 (20180614)
---------------------

* Don't raise a error when learning a too big email spam (spamc return code
  98).
* Password is now stored as json data file.
* Using standard cache *xdg_cache_home* to store information, usually
  *$HOME/.cache/isbg/*. If you have stored your password with and old releases
  you should re-store it and delete the old stored files, you should find the
  old ones as *$HOME/.isbg*.
* We use *cchardet* and *chardet* if installed for better detect the mails
  encoding.
* A more robust package, it can be used as a module and a script.
* Using isbg/__main__ or ``python -m isbg`` to run as script.
* python3 support.
* Modularized.
* Added a default --partialrun of 50. Use ``--partialrun=0`` to retain the
  old behaviour.
* Renamed sa_unwrap script to isbg_sa_unwrap, added command line options.
  Now it also depends of docopt.
* Documentation:
  * Use sphinx and support to upload it to `Read the docs`__.
  * Added development documentation.
  * Added manpages, built with sphinx.
* Examples: added a crontab example in the bash_scripts directory.

.. __: https://isbg.readthedocs.io/

Old Releases
------------

isbg 1.00 (20160106)
~~~~~~~~~~~~~~~~~~~~
  * The CLI interface is now implemented with docopt
  * The README now includes the documentation
  * New command --imaplist lists the directories in IMAP account
  * Code now follows PEP-8 style guide
  * Renamed variables to be consistent
  * Added gmail integration (thanks to Orkim!)
  * Added bash scripts for use with multiple accounts
  * SSL is now used by default and "--ssl" parameter is now a "--nossl" parameter
  * New command "--trackfile" now permits trackfile name configuration (thanks naevtamarkus!)
  * New command "--partialrun" now enable isbg to run for only a few emails (thanks naevtamarkus!)

isbg 0.99 (20100303)
~~~~~~~~~~~~~~~~~~~~
  * Drastic speed enhancement (thanks to Ajenbo!)
  * deletehighterthen, fix expunge, movehamto (thanks to AJenbo!)
  * Learn spam/ham before scanning
  * Call IMAP SEARCH command instead of fetching and checking manually
  * Ignore lockfile when too old (4h by default)
  * Switch to ignore lockfile
  * Bug fix: SSL now work.
  * Don't crash anymore when parsing weird attachement (like MS Office files)

isbg 0.98 (20091201)
~~~~~~~~~~~~~~~~~~~~
  * Teach spam and ham from specific folders
  * Compatibility from py2.4 to py2.6
