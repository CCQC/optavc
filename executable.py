__all__ = ['Executable', 'which', 'ProcessError']

import os
import sys
import re
import subprocess
import inspect

#import vulcan.util.tty as tty
#import vulcan
#import vulcan.error


class Executable(object):
    """Class representing a program that can be run on the command line."""

    def __init__(self, name):
        self.exe = name.split(' ')
        self.returncode = None

        if not self.exe:
            raise RuntimeError("Cannot construct executable for '%s'" % name)

    def add_default_arg(self, arg):
        self.exe.append(arg)

    @property
    def command(self):
        return ' '.join(self.exe)

    def __call__(self, *args, **kwargs):
        """Run this executable in a subprocess.

        Arguments
          args
            command line arguments to the executable to run.

        Optional arguments

          fail_on_error

            Raise an exception if the subprocess returns an
            error. Default is True.  When not set, the return code is
            available as `exe.returncode`.

          ignore_errors

            An optional list/tuple of error codes that can be
            *ignored*.  i.e., if these codes are returned, this will
            not raise an exception when `fail_on_error` is `True`.

          output, error

            These arguments allow you to specify new stdout and stderr
            values.  They default to `None`, which means the
            subprocess will inherit the parent's file descriptors.

            You can set these to:
            - python streams, e.g. open Python file objects, or os.devnull;
            - filenames, which will be automatically opened for writing; or
            - `str`, as in the Python string type. If you set these to `str`,
               output and error will be written to pipes and returned as
               a string.  If both `output` and `error` are set to `str`,
               then one string is returned containing output concatenated
               with error.

          input

            Same as output, error, but `str` is not an allowed value.

        Deprecated arguments

          return_output[=False]

            Setting this to True is the same as setting output=str.
            This argument may be removed in future Vulcan versions.

        """
        fail_on_error = kwargs.pop("fail_on_error", True)
        ignore_errors = kwargs.pop("ignore_errors", ())
        environ = os.environ.copy()
        environ.update(kwargs.pop('env', {}))

        # TODO: This is deprecated.  Remove in a future version.
        return_output = kwargs.pop("return_output", False)

        # Default values of None says to keep parent's file descriptors.
        if return_output:
            output = str
        else:
            output = kwargs.pop("output", None)

        error = kwargs.pop("error", None)
        input = kwargs.pop("input", None)
        if input is str:
            raise ValueError("Cannot use `str` as input stream.")

        def streamify(arg, mode):
            # if isinstance(arg, basestring):
            #     return open(arg, mode), True
            if arg is str:
                return subprocess.PIPE, False
            else:
                return arg, False

        ostream, close_ostream = streamify(output, 'w')
        estream, close_estream = streamify(error, 'w')
        istream, close_istream = streamify(input, 'r')

        # if they just want to ignore one error code, make it a tuple.
        if isinstance(ignore_errors, int):
            ignore_errors = (ignore_errors, )

        quoted_args = [arg for arg in args if re.search(r'^"|^\'|"$|\'$', arg)]
        if quoted_args:
            print(
                "Quotes in command arguments can confuse scripts like configure.",
                "The following arguments may cause problems when executed:",
                str("\n".join(["    " + arg for arg in quoted_args])),
                "Quotes aren't needed because vulcan doesn't use a shell.",
                "Consider removing them")

        cmd = self.exe + list(args)

        cmd_line = ' '.join(cmd)
        # tty.debug(cmd_line)

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=istream,
                stderr=estream,
                stdout=ostream,
                env=environ)
            out, err = proc.communicate()

            rc = self.returncode = proc.returncode
            if fail_on_error and rc != 0 and (rc not in ignore_errors):
                raise RuntimeError(
                    "Command exited with status %d:" % proc.returncode,
                    cmd_line)

            if output is str or error is str:
                result = ''
                if output is str: result += out.decode("utf-8")
                if error is str: result += err.decode("utf-8")
                return result

        except OSError as e:
            raise RuntimeError("%s: %s" % (self.exe[0], e.strerror),
                               "Command: " + cmd_line)

        except subprocess.CalledProcessError as e:
            if fail_on_error:
                raise RuntimeError(
                    str(e), "\nExit status %d when invoking command: %s" %
                    (proc.returncode, cmd_line))

        finally:
            if close_ostream: output.close()
            if close_estream: error.close()
            if close_istream: input.close()

    def __eq__(self, other):
        return self.exe == other.exe

    def __neq__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((type(self), ) + tuple(self.exe))

    def __repr__(self):
        return "<exe: %s>" % self.exe

    def __str__(self):
        return ' '.join(self.exe)


def which(name, **kwargs):
    """Finds an executable in the path like command-line which."""
    path = kwargs.get('path', os.environ.get('PATH', '').split(os.pathsep))
    required = kwargs.get('required', False)

    if not path:
        path = []

    for dir in path:
        exe = os.path.join(dir, name)
        if os.path.isfile(exe) and os.access(exe, os.X_OK):
            return Executable(exe)

    if required:
        print("Requires %s.  Make sure it is in your path." % name)
        sys.exit(1)

    return None


if __name__ == "__main__":

    print(which("ls"))

    ls = Executable("ls")
    result = ls("-l", output=str)
    print(result)

    #vulcan = Executable("/opt/vulcan/bin/vulcan")
    #vulcan('submit','-h')
