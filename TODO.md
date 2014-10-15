<h1> Todo list </h1>

<h2> High priority </h2>
* Write program as main()
* Correct the use of subprocess Popen (pipe.communicate() is the way to go)
* Delete the semi-encryption of passwords (Security through obscurity !=
  security)

<h2> Other stuff </h2>
* Auto report messages to Razor (high scoring ones that are definitely spam)
* Delete the semi-encryption of passwords (Security through obscurity !=
  security)
* Seperate out messages that may be false positives (scores
  close to SpamAssassin thresholds) from the definite spam ones.
* Integrate multiple accounts function to main program
    * a conf file in the working dir by default (/etc/isbg/ in Debian)
    * no encryption (too complicated atm, but would be nice)
