"""String interpolation for Python (by Ka-Ping Yee, 14 Feb 2000).

Modified by Henrik Levkowetz 28 Aug 2005, as follows:
    * Added a few doctest samples, invoked when module is run standalone
    * Changed syntax for invocation of arbitrary python expressions from
      ${arbitrary expression} to $[arbitrary expression]
    * Added shell invocation with $(arbitrary shell command)
    * Changed names of several of the functions to be (maybe?) more readable:
        - Iplt -> Interpolator
        - iplt -> interpolate
        - printpl -> iprint

This module lets you quickly and conveniently interpolate values into
strings (in the flavour of Perl or Tcl, but with less extraneous
punctuation).  You get a bit more power than in the other languages,
because this module allows subscripting, slicing, function calls,
attribute lookup, or arbitrary expressions.  Variables and expressions
are evaluated in the namespace of the caller.

The interpolate() function returns the result of interpolating a string, and
iprint() prints out an interpolated string.  Here are some examples:

    from interpolator import iprint
    iprint("Here is a $string.")
    iprint("Here is a $module.member.")
    iprint("Here is an $object.member.")
    iprint("Here is a $functioncall(with, arguments).")
    iprint("Here is an $[arbitrary + expression].")
    iprint("Here is an $array[3] member.")
    iprint("Here is a $dictionary['member'].")
    iprint("Here is an $(echo 'shell command' | tr "s" "S").")

    >>> from interpolate import iprint
    >>> string = "String"
    >>> iprint("Here is a $string.")
    Here is a String.
    >>> iprint("Here is module member $os.listdir.")
    Here is module member <built-in function listdir>.
    >>> object=Interpolator("")
    >>> iprint("Here is object member $object.__init__.")
    Here is object member <bound method Interpolator.__init__ of <Interpolator ''>>.
    >>> iprint("Here is the result of a funciton call: $len('Hello world').")
    Here is the result of a funciton call: 11.
    >>> iprint("Here is arbitrary expression $[1 + 2].")
    Here is arbitrary expression 3.
    >>> array = [0, "1", 2, "Yup"]
    >>> iprint("Here is array member $array[3].")
    Here is array member Yup.
    >>> dictionary = {'hello': 1, 'member': "dictionary member"}
    >>> iprint("Here is a $dictionary['member'].")
    Here is a dictionary member.
    >>> iprint("Here is a $(echo -n 'phell command' | tr 'p' 's').")
    Here is a shell command.


The filter() function filters a file object so that output through it
is interpolated.  This lets you produce the illusion that Python knows
how to do interpolation:

    >>> import interpolate
    >>> sys.stdout = interpolate.filter()
    >>> f = "fancy"
    >>> print "Isn't this $f?"
    Isn't this fancy?
    >>> print "Standard output has been replaced with a $sys.stdout object." #doctest: +ELLIPSIS
    Standard output has been replaced with a <interpolated <doctest._SpoofOut instance at 0x...>> object.
    >>> sys.stdout = interpolate.unfilter()
    >>> print "Okay, back $to $normal."
    Okay, back $to $normal.

Under the hood, the Interpolator class represents a string that knows how to
interpolate values.  An instance of the class parses the string once
upon initialization; the evaluation and substitution can then be done
each time the instance is evaluated with str(instance).  For example:

    >>> from interpolate import Interpolator
    >>> s = Interpolator("Here is $foo.")
    >>> foo = 5
    >>> print str(s)
    Here is 5.
    >>> foo = "bar"
    >>> print str(s)
    Here is bar.
    
"""

import sys, string, os
from types import StringType
from tokenize import tokenprog
import shlex

import syslog
syslog.openlog("postconfirmd", syslog.LOG_PID)
syslog.syslog("Loading '%s' (%s)" % (__name__, __file__))

class InterpolatorError(ValueError):
    def __init__(self, text, pos):
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

def pymatchorfail(text, pos):
    match = tokenprog.match(text, pos)
    if match is None:
        raise InterpolatorError(text, pos)
    return match, match.end()

def shmatchorfail(text, pos):
    lex = shlex.shlex(text[pos:], "'%s...'" % text[pos:pos+6])
    while text[pos] in lex.whitespace:
        pos = pos+1
    match = lex.get_token()
    if match is None:
        raise InterpolatorError(text, pos)
    return match, pos+len(match)

class Interpolator:
    """Class representing a string with interpolation abilities.
    
    Upon creation, an instance works out what parts of the format
    string are literal and what parts need to be evaluated.  The
    evaluation and substitution happens in the namespace of the
    caller when str(instance) is called."""

    def __init__(self, format, loc=None, glob=None):
        """The single argument to this constructor is a format string.

        The format string is parsed according to the following rules:

        1.  A dollar sign and a name, possibly followed by any of: 
              - an open-paren, and anything up to the matching paren 
              - an open-bracket, and anything up to the matching bracket 
              - a period and a name 
            any number of times, is evaluated as a Python expression.

        2.  A dollar sign immediately followed by an open-paren, and
            anything up to the matching close-paren, is evaluated as
            a Python expression.

        3.  Outside of the expressions described in the above two rules,
            two dollar signs in a row give you one literal dollar sign."""

        if type(format) != StringType:
            raise TypeError, "needs string initializer"
        self.format = format
        self.loc = loc
        self.glob = glob
        
        namechars = "abcdefghijklmnopqrstuvwxyz" \
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
        chunks = []
        pos = 0

        while 1:
            dollar = string.find(format, "$", pos)
            if dollar < 0: break
            if dollar > 0:
                prevchar = format[dollar-1]
            else:
                prevchar = ""
            nextchar = format[dollar+1]

            if prevchar == "\\":
                chunks.append((0, format[pos:dollar]))
                pos = dollar + 1

            elif nextchar == "[":
                chunks.append((0, format[pos:dollar]))
                pos, level = dollar+2, 1
                while level:
                    match, pos = pymatchorfail(format, pos)
                    tstart, tend = match.regs[3]
                    token = format[tstart:tend]
                    if token == "[": level = level+1
                    elif token == "]": level = level-1
                chunks.append((1, format[dollar+2:pos-1]))

            elif nextchar == "(":
                chunks.append((0, format[pos:dollar]))
                pos, level = dollar+2, 1
                while level:
                    token, pos = shmatchorfail(format, pos)
                    if token == "(": level = level+1
                    elif token == ")": level = level-1
                chunks.append((2, format[dollar+2:pos-1]))

            elif nextchar in namechars:
                chunks.append((0, format[pos:dollar]))
                match, pos = pymatchorfail(format, dollar+1)
                while pos < len(format):
                    if format[pos] == "." and \
                        pos+1 < len(format) and format[pos+1] in namechars:
                        match, pos = pymatchorfail(format, pos+1)
                    elif format[pos] in "([":
                        pos, level = pos+1, 1
                        while level:
                            match, pos = pymatchorfail(format, pos)
                            tstart, tend = match.regs[3]
                            token = format[tstart:tend]
                            if token[0] in "([": level = level+1
                            elif token[0] in ")]": level = level-1
                    else: break
                chunks.append((1, format[dollar+1:pos]))

            else:
                chunks.append((0, format[pos:dollar+1]))
                pos = dollar + 1

        if pos < len(format): chunks.append((0, format[pos:]))
        self.chunks = chunks

    def __repr__(self):
        return "<Interpolator " + repr(self.format) + ">"

    def __str__(self):
        """Evaluate and substitute the appropriate parts of the string."""
        try: 1/0
        except: frame = sys.exc_traceback.tb_frame

        while frame.f_globals["__name__"] == __name__: frame = frame.f_back
        if self.loc:
            loc = self.loc
        else:
            loc = frame.f_locals
        if self.glob:
            glob = self.glob
        else:
            glob = frame.f_globals

        result = []
        for live, chunk in self.chunks:
            if live == 1:
                result.append(str(eval(chunk, loc, glob)))
            elif live == 2:
                for key in glob.keys():
                    if type(glob[key]) == type(""):
                        os.environ[key] = glob[key]
                for key in loc.keys():
                    if type(loc[key]) == type(""):
                        os.environ[key] = loc[key]
                pipe = os.popen(chunk, "r")
                result.append(pipe.read().rstrip())
                pipe.close()
            else:
                result.append(chunk)

        return string.join(result, "")

def interpolate(text, loc=None, glob=None): return str(Interpolator(text, loc, glob))
def iprint(text): print interpolate(text)

class InterpolatorFile:
    """A file object that filters each write() through an interpolator."""
    def __init__(self, file): self.file = file
    def __repr__(self): return "<interpolated " + repr(self.file) + ">"
    def __getattr__(self, attr): return getattr(self.file, attr)
    def write(self, text): self.file.write(str(Interpolator(text)))

def filter(file=sys.stdout):
    """Return an InterpolatorFile that filters writes to the given file object.
    
    'file = filter(file)' replaces 'file' with a filtered object that
    has a write() method.  When called with no argument, this creates
    a filter to sys.stdout."""
    return InterpolatorFile(file)

def unfilter(ifile=None):
    """Return the original file that corresponds to the given InterpolatorFile.
    
    'file = unfilter(file)' undoes the effect of 'file = filter(file)'.
    'sys.stdout = unfilter()' undoes the effect of 'sys.stdout = filter()'."""
    return ifile and ifile.file or sys.stdout.file

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()

