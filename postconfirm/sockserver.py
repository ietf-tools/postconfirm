"""Python executable-serving system

ReadyExec is a client-server system designed to alleviate the
problem of high-startup-costing applications which are run
repeatedly (e.g., in procmail), and use stdio files, argv,
and exit codes interact can be used within ReadyExec with very
little work.

Introduction

There are two components to the ReadyExec system.
There is the readyexecd.py server and the readyexec client.


readyexecd.py:

  usage: readyexecd.py socket_path callable_object

readyexecd.py is a long-running daemon process that listens
on a unix domain socket, socket_path.  When it receives
requests on socket_path, it then executes callable_object,
which is the path to a Python callable object, e.g.,
module.function

While executing the callable object, it connects its
stdio file streams to the client, so that any standard
input, output, and error is able to be read in by the
completely unaware module.function.

See examples later in this document.

Note: readyexecd.py does not daemonize itself.


readyexec:

  usage: readyexec [--stop] socket_path program_args

readyexec is a short-lived client process that sends
a request to execute the code that the readyexecd.py listening
on socket_path is serving.  It sends its args, environment,
and stdio file descriptors to the server, and then
reads back an error code.

If --stop is given, it tells the server to shutdown.

See examples later in this document.


How to get your Python script using ReadyExec:

If you have a script that would like to make use of ReadyExec,
merely make a module that can be imported containing a
function which runs your script-specfic code.
Your sys.argv and sys.std* filehandles will be replaced
in the background, so users running readyexec will be
able to communicate with your process in a 'normal' fashion.
Also, if you raise an exception or call sys.exit, readyexec
will exit with the appropriate exit code (else exiting with 0)..

Note that you also have access to readyexec's environment variables.


Examples

Assuming that mymodule.foobar is a Python function:

  readyexecd.py /tmp/foobar mymodule.foobar

Now, we can 'call' mymodule.foobar, passing in 'args'
(note that these are not arguments to the function, but
rather just put into the argument vector sys.argv
that mymodule.foobar can read)

  readyexec /tmp/foobar
  readyexec /tmp/foobar arg1 arg2
  readyexec /tmp/foobar < input > output


Author

   Frank J. Tobin, ftobin@neverending.org

   OpenPGP key fingerprint:
   4F86 3BBB A816 6F0A 340F  6003 56FF D10A 260C 4FA3

Copyright

   Copyright (C) 2001 Frank J. Tobin, ftobin@neverending.org

   This library is free software; you can redistribute it and/or modify
   it under the terms of the GNU Lesser General Public License as
   published by the Free Software Foundation; either version 2.1 of the
   License, or (at your option) any later version.

   This library is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
   Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public
   License along with this library; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
   USA or see http://www.gnu.org/copyleft/lesser.html
"""

import sys
import os
import os.path
import SocketServer
import socket
import signal
import traceback
import fdpass
import syslog


__author__   = "Frank J. Tobin, ftobin@neverending.org"
# if you update the version here bump the setup.py too!
__version__  = "0.4.0.p3"
__revision__ = "" # Was: $Id: readyexec.py,v 1.28 2002/10/10 01:44:22 ftobin Exp $

stds = ('stdin', 'stdout', 'stderr')

syslog.openlog("postconfirmd", syslog.LOG_PID)
syslog.syslog("Loading '%s' (%s)" % (__name__, __file__))

class ProtocolError(Exception):
    pass

class TimeoutError(Exception):
    pass

class Singleton(object):
    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get('__it__')
        if it is None:
            cls.__it__ = object.__new__(cls)
        return cls.__it__

class Output(Singleton):

    quiet = 0
    do_debug = 0
    #syslog.openlog("sockserver", syslog.LOG_PID)
    def __init__(self, quiet=None, debug=None):
        if quiet is not None: self.quiet = quiet
        if debug is not None: self.do_debug = debug
    def data(self, msg):
        print msg
    def err(self, msg):
        syslog.syslog('%s\n' % msg)
    def warn(self, msg):
        if not self.quiet: syslog.syslog('%s\n' % msg)
    def debug(self, msg):
        if self.do_debug: syslog.syslog('%s\n' % msg)


class ReadyExecHandler(SocketServer.StreamRequestHandler, object):
    """Assumes we are being called in a throw-away environment
    (e.g., a separate process), because we modify
    sys.stdin, sys.stdio, and sys.argv, without saving backups.
    """

    pretend_arg0_fmt = '(readyexec %s)'
    negotiate_secs   = 10
    handler_timeout  = 300

    # We need the rbufsize to be unbuffered because
    # fdpass takes a socket file descriptor, and
    # that screws up the stdio buffering.
    rbufsize         = 0
    
    do_read_args     = True
    do_read_env      = True
    do_read_fd_names = True
    
    def __init__(self, request, client_address, server):
        self.output = Output()
        self.pretend_arg0 = self.pretend_arg0_fmt % self.to_run_path
        super(ReadyExecHandler, self).__init__(request,
                                               client_address, server)

    def handle(self):
        signal.signal(signal.SIGALRM, socket_read_timeout_handler)
        signal.alarm(self.negotiate_secs)
        try:
            op = self.read_string()
        except TimeoutError:
            raise SystemExit(4)

        signal.alarm(0)

        if op == 'conduit':
            self.handle_conduit()
        elif op == 'stop':
            self.handle_stop()
        else:
            raise ProtocolError, "received unknown op %s" % repr(op)

    def handle_conduit(self):
        pid = os.fork()

        if pid == 0:
            try:
                self.handle_conduit_as_subchild()
            except SystemExit, e:
                exit_code = int(str(e))
            except:
                exit_code = 3
                self.output.err(traceback.format_exc().replace('\n','\\n'))
            else:
                exit_code = 0
            os._exit(exit_code)
        
        self.output.debug("waiting on child")
        pid, status = os.waitpid(pid, 0)

        signal.signal(signal.SIGALRM, socket_write_timeout_handler)
        signal.alarm(self.negotiate_secs)
        try:
            self.tell_exit(status >> 8)
        except TimeoutError:
            return

    def handle_conduit_as_subchild(self):
        sys.argv = [self.pretend_arg0]
        signal.signal(signal.SIGALRM, socket_read_timeout_handler)
        signal.alarm(self.negotiate_secs)
        new_std_fds = {}
        
        try:
            if self.do_read_args:
                args = self.read_args()
                self.output.debug("read args %s" % args)
                sys.argv.extend(args)

            if self.do_read_env:
                os.environ = self.read_environ()
            
            for std in stds:
                fd = self.read_fd(std)
                new_std_fds[std] = fd
                self.output.debug("fd for %s is %d" % (std, fd))
            
            self.request.shutdown(0)
        except TimeoutError:
            raise SystemExit(4)
        signal.alarm(0)

        signal.signal(signal.SIGALRM, fd_setup_timeout_handler)
        signal.alarm(self.negotiate_secs)
        try:
            # want to iterate over these in a specific order
            for std in stds:
                std_base = '__%s__' % std
                fd = new_std_fds[std]
                current_file = getattr(sys, std_base)
                if current_file.mode == 'w':
                    current_file.flush()
                current_fno = current_file.fileno()
                os.dup2(fd, current_fno)
                newfile = os.fdopen(current_fno, current_file.mode)
                for s in std_base, std:
                    setattr(sys, s, newfile)
        except TimeoutError:
            raise SystemExit(4)
        signal.alarm(0)
        
        signal.signal(signal.SIGALRM, handler_timeout_handler)
        signal.alarm(self.handler_timeout)
        try:
            apply(self.to_run)
        except TimeoutError:
            raise SystemExit(4)
        finally:
            signal.signal(signal.SIGALRM, flush_timeout_handler)
            signal.alarm(self.negotiate_secs)
            try:
                for std in sys.stdout, sys.stderr:
                    std.flush()
            except TimeoutError:
                raise SystemExit(4)
        signal.alarm(0)


    def handle_stop(self):
        self.stop_server()
    
    def stop_server(self):
        os.kill(self.server.pid, signal.SIGTERM)

    def read_args(self):
        self.output.debug("expecting arguments")
        self.verify_expected("args")
        argc = self.read_long()

        argv = []
        for i in xrange(argc):
            argv.append(self.read_string())

        return argv

    def read_fd(self, stream_name):
        self.output.debug("expecting %s fd" % stream_name)
        if self.do_read_fd_names:
            self.verify_expected(stream_name)
        return fdpass.recv_fd(self.request.fileno())

    def read_environ(self):
        self.output.debug("expecting environment")
        self.verify_expected('env')
        env = {}
        count = self.read_long()

        for i in range(count):
            self.output.debug("reading environment var %d" % (i+1))
            (key, value) = self.read_string().split('=', 1)
            env[key] = value

        return env
    
    def tell_exit(self, code):
        self.send_string("exit")
        self.send_long(code)

    def send_string(self, msg):
        self.output.debug("sending netstring: %s" % repr(msg))
        self.wfile.write(netstring(msg))

    def send_long(self, msg):
        self.output.debug("sending netint: %s" % repr(msg))
        self.wfile.write(netint(msg))

    def read_string(self):
        s = read_netstring(self.rfile)
        self.output.debug("read string %s" % repr(s))
        return s

    def read_long(self):
        l = read_netint(self.rfile)
        self.output.debug("read long %s" % repr(l))
        return l

    def verify_expected(self, expected):
        got = self.read_string()
        if got != expected:
            raise ProtocolError, \
                  "expected %s, got %s" % (repr(expected), repr(got))


class ReadyExec(SocketServer.ForkingMixIn,
                SocketServer.UnixStreamServer, object):
    handled_signals = [signal.SIGINT, signal.SIGTERM]
    
    def __init__(self, to_run, cs_path, quiet=0, debug=0):
        self.output = Output(quiet=quiet, debug=debug)

        assert callable(to_run), ("%s is not callable" % to_run)
        to_run_path = "%s.%s" % (to_run.__module__, to_run.func_name)
        
        ReadyExecHandler.to_run      = staticmethod(to_run)
        ReadyExecHandler.to_run_path = to_run_path

        self.install_signal_handlers()
        
        self.output.debug("listening on %s" % cs_path)
        super(ReadyExec, self).__init__(cs_path, ReadyExecHandler)

    def handle_signal(self, sig, frame):
        syslog.syslog("Terminating.")
        sys.exit()
    handle_signal = classmethod(handle_signal)

    def install_signal_handlers(self):
        for sig in self.handled_signals:
            signal.signal(sig, self.handle_signal)
    install_signal_handlers = classmethod(install_signal_handlers)

    def reset_signal_handlers(self):
        for sig in self.handled_signals:
            signal.signal(sig, signal.SIG_DFL)
    reset_signal_handlers = classmethod(reset_signal_handlers)

    def server_close(self):
        if os.path.exists(self.server_address):
            os.unlink(self.server_address)
        super(ReadyExec, self).server_close()

    def handle_request(self):
        """Overriding so that there is no try statement around
        process_request"""
        try:
            request, client_address = self.get_request()
        except socket.error:
            return

        if self.verify_request(request, client_address):
            self.process_request(request, client_address)
            self.close_request(request)

    def process_request(self, request, address):
        """Fork a new subprocess to process the request.
        Overriding ForkingMixin to not trap exceptions
        """
        # we set the pid here in case we've forked after __init__
        # was called
        if not hasattr(self, 'pid'):
            self.pid = os.getpid()
            
        self.collect_children()
        pid = os.fork()

        if pid == 0:
            # Child process.
            # This must never return, hence os._exit()!
            try:
                self.finish_request(request, address)
            except SystemExit, e:
                exit_code = int(str(e))
            except Exception, e:
                exit_code = 4
                self.output.err(traceback.format_exc().replace('\n','\\n'))
            else:
                exit_code = 0
            os._exit(exit_code)

        # Parent process
        if self.active_children is None:
            self.active_children = []
        self.active_children.append(pid)
        self.close_request(request)

    def finish_request(self, request, address):
        # We reset the signal handlers so that if a child
        # process receives a signal it doesn't affect the head
        # server.
        # Note: this is the first thing that gets executed
        # in the child process.
        self.reset_signal_handlers()
        super(ReadyExec, self).finish_request(request, address)


def netint(i):
    """Returns a netint for i"""
    return "%d," % i

def read_netint(f):
    """Returns the next netint from file f"""
    (l, c) = read_uint(f)
    expect_term = ','
    if c != expect_term:
        raise ProtocolError, \
              "invalid netint termination: expected %c, got %c" \
              % (repr(expect_term), repr(c))
    return long(l)


def netstring(str):
    """Returns a netstring for str
    http://cr.yp.to/proto/netstrings.txt"""
    return "%d:%s," % (len(str), str)


def read_netstring(f):
    """Returns the next netstring read from file f

    http://cr.yp.to/proto/netstrings.txt"""
    (length, c) = read_uint(f)
    expect_term = ':'
    if c != expect_term:
        raise ProtocolError, \
              "invalid netstring length termination: expected %c, got %c" \
              % (repr(expect_term), repr(c))

    
    s = f.read(length)
    expect_term = ','
    c = f.read(1)
    if c != expect_term:
        raise ProtocolError, \
              "invalid netstring termination: expected %c, got %c" \
              % (repr(expect_term), repr(c))

    return s


def read_uint(f, maxdigits=4):
    """This is an ugly hack to deal with the lack of a nice
    stdio-buffering layer on top of sockets so that
    I can read things with scanf() easily

    Note to self: look into recv(2)'s MSG_PEEK
    
    returns (int, terminator)
    """
    n = ''
    i = 0
    
    for i in range(maxdigits+1):
        c = f.read(1)
        if not c.isdigit():
            if not c:
                raise ProtocolError, "received EOF while expecting uint"
            if not n:
                raise ProtocolError, "long cannot start with %s" \
                      % repr(c)
            return (long(n), c)
        n += c

    raise ProtocolError, "%s is getting to be too long" % repr(n)


def socket_read_timeout_handler(signum, frame):
    msg = "Timeout waiting for negotiation on socket"
    syslog.syslog(msg)
    raise TimeoutError(msg)

def socket_write_timeout_handler(signum, frame):
    msg = "Timeout waiting for socket write to complete"
    syslog.syslog(msg)
    raise TimeoutError(msg)

def fd_setup_timeout_handler(signum, frame):
    msg = "Timeout waiting for file descriptor setup"
    syslog.syslog(msg)
    raise TimeoutError(msg)

def handler_timeout_handler(signum, frame):
    msg = "Timeout waiting for handler to complete"
    syslog.syslog(msg)
    raise TimeoutError(msg)

def flush_timeout_handler(signum, frame):
    msg = "Timeout waiting for output streams to be flushed"
    syslog.syslog(msg)
    raise TimeoutError(msg)
