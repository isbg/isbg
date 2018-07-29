News [#]_
=========

Unreleased
----------

New in 2.1.0
~~~~~~~~~~~

* Use of standard localization folders. You must store your password again.
* Added documentation in `Read the docs`__.
* Added a default `--partialrun` of 50.

.. __: https://isbg.readthedocs.io/


New in 1.00
~~~~~~~~~~~

**DEPRECATION NOTICE:** if you used the `--ssl` parameter in 0.99, you now
need to stop using it! SSL is now used by default. If you want not to use
it, please use the `--nossl` parameter.

* The CLI interface is now implemented with docopt.
* The README now includes the documentation.
* New command `--imaplist` lists the directories in IMAP account.
* Code now follows PEP-8 style guide.
* Renamed variables to be consistent.
* Added gmail integration (thanks to Orkim!).
* Added bash scripts for use with multiple accounts.
* SSL is now used by default and "--ssl" parameter is now a "--nossl"
  parameter.
* New command `--trackfile` now permits trackfile name configuration (thanks
  naevtamarkus!).
* New command `--partialrun` now enable isbg to run for only a few emails
  (thanks naevtamarkus!).


.. [#] To read a more detailed information about changes, see :doc:`CHANGELOG`.
