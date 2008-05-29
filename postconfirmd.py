#!/usr/bin/python
# -*- python -*-

"""
NAME
	%(program)s - Mail confirmation system (daemon part)

SYNOPSIS
	%(program)s [OPTIONS]

DESCRIPTION
        %(program)s is the long-running (daemon) part of a client-server
        program which handles email confirmations. It is intended as a
        front-end to mailing lists. It provides funcitonality which is a
        subset of TMDA, but is adapted to high-volume usage and does not have
        anywhere near all the bells and whistles which TMDA has. On the other
        hand, since the whitelist lookup is done by the long-running server
        part, the overhead of doing a verification that a poster has a
        confirmed address is much smaller than for TMDA.

%(options)s

AUTHOR
	Written by Henrik Levkowetz, <henrik@merlot.tools.ietf.org>. Uses the
        daemonize module from Chad J. Schroeder, from the Python Cookbook at
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731, and
        the readyexec module from Frank J. Tobin, available at
        http://readyexec.sourceforge.net/.

COPYRIGHT
	Copyright 2008 Henrik Levkowetz

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License, or (at
	your option) any later version. There is NO WARRANTY; not even the
	implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
	PURPOSE. See the GNU General Public License for more details.

"""

import re
import sys
import os.path
import getopt
import sockserver
import daemonize
import service
import config
import StringIO

# ------------------------------------------------------------------------------
# Misc. metadata

version = "v0.10"
program = os.path.basename(sys.argv[0])
progdir = os.path.dirname(sys.argv[0])

# ------------------------------------------------------------------------------
# Utility functions

def mkdir(path):
    if not os.path.exists(path):
        print "Creating directory '%s'" % path
        os.mkdir(path)
        return True
    return False

def mkfile(file):
    path = os.path.dirname(file)
    mkdir(path)
    if not os.path.exists(file):
        os.mknod(file)
        return True
    return False

# ------------------------------------------------------------------------------
# Read config file


merger = config.ConfigMerger(lambda x, y, z: "overwrite")

default = """
mail_template:	"/etc/postconfirm/confirm.mail.template"
mail_cache_dir:	"/var/cache/postconfirm"
key_file:	"/etc/postconfirm/hash.key"
smtp_host:	localhost
foreground:     False
debug:          False
whitelists:     [ "/etc/postconfirm/whitelist", ]
confirmlist:    "/var/run/postconfirm/confirmed"
"""

default = StringIO.StringIO(default)
conf = config.Config(default)

for conffile in ["/etc/postconfirm.conf",
                "/etc/postconfirm/postconfirm.conf",
                progdir+"/postconfirm.conf",
                os.getcwd()+"/postconfirm.conf",
            ]:
    if os.path.exists(conffile):
        merger.merge(conf, config.Config(conffile))

# import pprint
# pprint.pprint(dict(conf), sys.stdout, 4, 40)

# ------------------------------------------------------------------------------
# Some assertions
assert(os.path.exists(conf.mail_template))
assert(type(conf.whitelists) == config.Sequence)

# ------------------------------------------------------------------------------
# Create directories and do initialization, as needed:

mkdir(conf.mail_cache_dir)

if mkfile(conf.key_file):
    keyfile = open(conf.key_file, "w")
    keyfile.write(os.urandom(128))
    keyfile.close()

mkfile(conf.confirmlist)

# ------------------------------------------------------------------------------
# Create list of options, for the help text

options = ""
for line in re.findall("\n +(if|elif) +opt in \[(.+)\]:\s+#(.+)\n", open(sys.argv[0]).read()):
    if not options:
        options += "OPTIONS\n"
    options += "        %-16s %s\n" % (line[1].replace('"', ''), line[2])
options = options.strip()

# ------------------------------------------------------------------------------
# Process options

# with ' < 1:' on the next line, this is a no-op:
if len(sys.argv) < 1:
    print __doc__ % locals()
    sys.exit(1)

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], "dfhsV", ["debug", "foreground", "help", "socket", "version", ])
except Exception, e:
    print "%s: %s" % (program, e)
    sys.exit(1)

# process option switches
for opt, value in opts:
    if not opt:
        pass
    elif opt in ["-d", "--debug"]:      # Run with debug output
        conf.debug = True
    elif opt in ["-f", "--foreground"]: # Run in the foreground, don't daemonize
        conf.foreground = True
    elif   opt in ["-h", "--help"]:     # Output this help, then exit
        print __doc__ % globals()
        sys.exit(1)
    elif opt in ["-V", "--version"]:    # Output version, then exit
        print program, version
        sys.exit(0)

# ------------------------------------------------------------------------------
# Set up logging

import syslog
syslog.openlog("postconfirm", syslog.LOG_PID, syslog.LOG_DAEMON)
log = syslog.syslog

# ------------------------------------------------------------------------------
# set default values, if any
socket_path = "/var/run/postconfirm/socket" % globals()
mkdir(os.path.dirname(socket_path))
sys.stderr.write("Will listen on unix domain socket '%s'\n" % socket_path)


# ------------------------------------------------------------------------------
# Set up the service
service.setup(conf, args)

# ------------------------------------------------------------------------------
# Maybe daemonize
if not conf.foreground:
    log("Postconfirm daemon starting.")
    sys.stderr.write("Daemonizing...\n")
    daemonize.createDaemon()
else:
    sys.stderr.write("Not daemonizing.\n")

# ------------------------------------------------------------------------------
# connect stdout and stderr to syslog, to catch messages, exceptions, traceback
syslog.write = syslog.syslog
sys.stdout = syslog
sys.stderr = syslog

# ------------------------------------------------------------------------------
# Start the server
server = sockserver.ReadyExec(service.handler, socket_path, debug=conf.debug)
try:        
    server.serve_forever()
finally:
    server.server_close()

