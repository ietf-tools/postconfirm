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

FILES
        %(program)s reads its configuration from the following files (if found),
        in the given order:
        
            <bin-dir>/postconfirm.conf
            /etc/postconfirm.conf
            /etc/postconfirm/postconfirm.conf
            ~/.postconfirmrc

        where <bin-dir> is the directory where postconfirmd is installed.

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
import stat
import getopt
import config
import StringIO

# ------------------------------------------------------------------------------
# Misc. metadata

version = "0.23"
program = os.path.basename(sys.argv[0])
progdir = os.path.dirname(sys.argv[0])

# ------------------------------------------------------------------------------
# Read config file


merger = config.ConfigMerger(lambda x, y, z: "overwrite")

default = """
foreground:     False
debug:          False
"""

default = StringIO.StringIO(default)
conf = config.Config(default)

for conffile in [progdir+"/postconfirm.conf",
                "/etc/postconfirm.conf",
                "/etc/postconfirm/postconfirm.conf",
                os.path.expanduser("~/.postconfirmrc"),
            ]:
    if os.path.exists(conffile):
        merger.merge(conf, config.Config(conffile))

# import pprint
# pprint.pprint(dict(conf), sys.stdout, 4, 40)

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

import syslog
import sockserver
import daemonize
import service
import pwd
import grp
    
# ------------------------------------------------------------------------------
# Set up logging

syslog.openlog("postconfirmd", syslog.LOG_PID)
log = syslog.syslog

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
# set default values, if any
socket_path = "/var/run/postconfirm/socket" % globals()
mkdir(os.path.dirname(socket_path))



# ------------------------------------------------------------------------------
# Maybe daemonize

# Get user and group we should execute as
user, pwd, uid, gid, gecos, home, shell = list(pwd.getpwnam(conf.daemon_user))
if "daemon_group" in conf:
    group, gpwd, gid, members = list(grp.getgrnam(conf.daemon_group))

log("Postconfirm daemon v%s starting." % (version, ))
sys.stderr.write("\nPostconfirm daemon v%s starting.\n" % (version, ))
if not conf.foreground:
    pidfname = "/var/run/%s.pid" % program

    pidfile = open(pidfname, "w")
    os.chown(pidfile.name, uid, gid)
    pidfile.close()

    os.setgid(gid)
    os.setuid(uid)
    daemonize.createDaemon()

    pidfile = open(pidfname, "w")
    pidfile.write("%s" % os.getpid())
    pidfile.close()
else:
    log("Not daemonizing.")
    sys.stderr.write("Not daemonizing.\n")

sys.stderr.write("Will listen on unix domain socket '%s'\n" % socket_path)

# ------------------------------------------------------------------------------
# connect stdout and stderr to syslog, to catch messages, exceptions, traceback
log("Redirecting stdout and stderr to syslog")
syslog.write = syslog.syslog
sys.stdout = syslog
sys.stderr = syslog

# ------------------------------------------------------------------------------
# Set up the service
service.setup(conf, args)

# ------------------------------------------------------------------------------
# Start the server

server = sockserver.ReadyExec(service.handler, socket_path, debug=conf.debug)

os.chmod(socket_path, stat.S_IRWXU | stat.S_IRWXG )
try:        
    server.serve_forever()
finally:
    server.server_close()

