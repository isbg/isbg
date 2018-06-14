Manual page for isbg\_sa\_unwrap
================================

SYNOPSIS
--------

isbg\_sa\_unwrap [**--from** *<FROM\_FILE>*] [**--to** *<TO\_FILE>*]

isbg\_sa\_unwrap (**-h** \| **--help**)

isbg\_sa\_unwrap **--usage**

isbg\_sa\_unwrap.py **--version**


DESCRIPTION
-----------

isbg\_sa\_unwrap unwrap a mail bundled by *SpamAssassin*.

it parses a *rfc2822* email message and unwrap it if contains spam
attached.


OPTIONS
-------

**-h**, **--help**
    Show the help screen
**--usage**
    Show usage information
**--version**
    Show version information

**-f** *FILE*, **--from**\ =\ *FILE*
    Filename of the email to read and unwrap. If not informed, the stdin
    will be used
**-t** *FILE*, **--to**\ =\ *FILE*
    Filename to write the unwrapped email. If not informed, the stdout
    will be used

SEE ALSO
--------

`spamassassin(1)`,
`Mail::SpamAssassin::Conf(3)`.

The full documentation for isbg is maintained in https://isbg.readthedocs.io/

BUGS
----

You can report bugs on https://github.com/isbg/isbg/issues
