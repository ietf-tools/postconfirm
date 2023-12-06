
Caution
-------

This is an alpha release.  While the functionality is sound, the
packaging is probably not even beta quality.  Compilation of the
components written in C has only been tested under Linux.

Description
-----------

postconfirm consists of postconfirmd, which is the long-running
(daemon) part, and postconfirmc, which is the client part of a
client-server program which handles email confirmations. It is
intended as a front-end to mailing lists. It provides
funcitonality which is a subset of TMDA, but is adapted to
high-volume usage and does not have anywhere near all the bells
and whistles which TMDA has. On the other hand, since the
whitelist lookup is done by the long-running server part, the
overhead of doing a verification that a poster has a confirmed
address is much smaller than for TMDA.  This makes it a factor
1000 or more faster than TMDA in production, with a memory footprint
a factor 20 smaller.

Configuration
------------
The `wrapper` script in this project will import `wrapper-param` which is expected to contain the following configuration:
```
# this file of parameters included by the wrapper script

# the filter executable:
FILTER_BIN=/usr/bin/postconfirmc

# Mailman's distributed mailman executable:
MAILMAN_BIN=/usr/lib/mailman/mail/mailman

# Mail handler executable
SENDMAIL_BIN=/usr/sbin/sendmail

# Where we store mailman commands identified as spam
SPAM_STASH=/path/to/stash

# our forwarding alias
FORWARDSENDER=sender@domain.example

# the lists that do not go through postconfirm
NFLISTS=(listname1 listname2 listname3)

```

