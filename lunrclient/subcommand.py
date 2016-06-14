from __future__ import print_function

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import namedtuple
from os.path import basename
from textwrap import dedent

import inspect
import sys
import re


Option = namedtuple('Option', ['args', 'kwargs'])


def opt(*args, **kwargs):
    def decorator(method):
        if not hasattr(method, 'options'):
            method.options = []
        if args:
            # Append the option to our option list
            method.options.append(Option(args, kwargs))
        # No need to wrap, only adding an attr to the method
        return method
    return decorator


def noargs(method):
    method.options = []
    return method


class SubCommandError(Exception):
    pass


class SubCommandParser(object):

    def __init__(self, sub_commands, desc=None):
        self.sub_commands = self.build_dict(sub_commands)
        self.prog = None
        self.desc = desc

    def build_dict(self, sub_commands):
        result = {}
        for cmd in sub_commands:
            # If command is just an instance of 'object', ignore the cmd
            if cmd.__class__.__name__ == 'object':
                continue

            name = getattr(cmd, '_name', None)
            if not name:
                raise SubCommandError(
                    "object '%s' has no attribute '_name'; "
                    "please give your SubCommand class a name" % cmd
                )
            result[name] = cmd
        return result

    def run(self, args=None, prog=None):
        # use sys.argv if not supplied
        if not args:
            prog = basename(sys.argv[0])
            args = sys.argv[1:]
        self.prog = prog

        # If completion token found in args
        if '--bash-completion' in args:
            return self.bash_completion(args)

        # If bash completion script requested
        if '--bash-completion-script' in args:
            return self.bash_completion_script(prog)

        # Find a subcommand in the arguments
        for index, arg in enumerate(args):
            if arg in self.sub_commands.keys():
                # Remove the sub command argument
                args.pop(index)
                # Run the sub-command passing the remaining arguments
                return self.sub_commands[arg](args, prog)

        # Unable to find a suitable sub-command
        return self.help()

    def bash_completion_script(self, prog):
        print('_%(prog)s() {\n'
              '  local cur="${COMP_WORDS[COMP_CWORD]}"\n'
              '  local list=$(%(prog)s --bash-completion $COMP_LINE)\n'
              '  COMPREPLY=($(compgen -W "$list" $cur))\n'
              '}\n'
              'complete -F _%(prog)s %(prog)s\n' % locals())

    def bash_completion(self, args):
        # args = ['--bash-completion', '%prog', 'sub-command', 'command']
        try:
            # If a subcommand is already present
            if args[2] in self.sub_commands.keys():
                # Have the subcommand print out all possible commands
                return self.sub_commands[args[2]].bash_completion()
        except (KeyError, IndexError):
            pass

        # Print out all the possible sub command names
        print(' '.join(self.sub_commands.keys()))
        return 0

    def help(self):
        print("Usage: %s <command> [-h]\n" % self.prog)
        if self.desc:
            print(self.desc + '\n')

        print("Available Commands:")
        for name, command in self.sub_commands.iteritems():
            print("  ", name)
            # TODO: Print some help message for the commands?
        return 1


class CommandParser(SubCommandParser):

    def __init__(self, commands, desc=None):
        self.sub_commands = self.build_dict(commands)
        self.prog = None
        self.desc = desc

    def build_dict(self, commands):
        result = {}
        # get a listing of all the methods
        for cmd in commands:
            for (name, method) in cmd._commands.iteritems():
                result[name] = MethodWrapper(cmd, method)
        return result


class SubCommand(object):

    def __init__(self):
        # Return a dict of all methods with the options attribute
        self._commands = self.methods_with_opts()
        self.prog = None

    def pre_command(self):
        pass

    def bash_completion(self):
        print(' '.join(self._commands.keys()), end=' ')
        return 0

    def remove(self, haystack, needles):
        result = {}
        for key, value in haystack.items():
            if key not in needles:
                result[key] = value
        return result

    def opt(self, *args, **kwargs):
        if not hasattr(self, 'globals'):
            self.globals = []
        self.globals.append(Option(args, kwargs))

    def methods_with_opts(self):
        result = {}
        # get a listing of all the methods
        for name in dir(self):
            if name.startswith('__'):
                continue
            method = getattr(self, name)
            # If the method has an options attribute
            if hasattr(method, 'options'):
                name = re.sub('_', '-', name)
                result[name] = method
        return result

    def call_method(self, args, method):
        # Parse the arguments
        args = self.parse_args(method, args)
        # Determine the acceptable arguments
        (kwargs, unused) = self.acceptable_args(self.get_args(method),
                                                args)
        # Attach the unused options as class variables
        for key, value in unused.items():
            # Don't overwrite a method or some such
            if not hasattr(self, key):
                setattr(self, key, value)

        # If all args are rolled into 'args' the user should still
        # expect to find the args attached to the class
        if len(kwargs) == 1 and 'args' in kwargs:
            for key, value in kwargs['args'].items():
                # Don't overwrite a method or some such
                if not hasattr(self, key):
                    setattr(self, key, value)

        # Call the pre_command method now that args have been parsed
        self.pre_command()
        # Call the command with the command
        # line args as method arguments
        return method(**kwargs)

    def __call__(self, args, prog):
        self.prog = prog
        """
        Figure out which command for this sub-command should be run
        then pass the arguments to the commands parser
        """
        for index, arg in enumerate(args):
            # Find a command in the arguments
            if arg in self._commands.keys():
                # Get the method for the command
                method = self._commands[arg]
                # Remove the command from the args
                args.pop(index)
                # Call the method with the remaining arguments
                return self.call_method(args, method)

        # Unable to find the command
        return self.help()

    def parse_args(self, method, args):
        # create an argument parser
        parser = ArgumentParser(prog=method.__name__,
                                description=dedent(method.__doc__ or ''),
                                formatter_class=RawDescriptionHelpFormatter)
        # Add method options to the subparser
        for opt in method.options:
            parser.add_argument(*opt.args, **opt.kwargs)
        # Add global options to the subparser

        if hasattr(self, 'globals'):
            for opt in self.globals:
                parser.add_argument(*opt.args, **opt.kwargs)

        results = {}
        args = vars(parser.parse_args(args))
        # Convert dashes to underscore
        for key, value in args.items():
            results[re.sub('-', '_', key)] = value
        return results

    def help(self):
        print("Usage: %s %s <command> [-h]\n" % (self.prog, self._name))
        if self.__doc__:
            stripped = self.__doc__.strip('\n| ')
            print(re.sub(' ' * 4, '', stripped))

        print("\nAvailable Commands:")
        for name, command in self._commands.iteritems():
            print("  ", name)
            # print "  ", command.__doc__.strip('\n')
        return 1

    def get_args(self, func):
        """
        Get the arguments of a method and return it as a dictionary with the
        supplied defaults, method arguments with no default are assigned None
        """
        def reverse(iterable):
            if iterable:
                iterable = list(iterable)
                while len(iterable):
                    yield iterable.pop()

        args, varargs, varkw, defaults = inspect.getargspec(func)
        result = {}
        for default in reverse(defaults):
            result[args.pop()] = default

        for arg in reverse(args):
            if arg == 'self':
                continue
            result[arg] = None

        return result

    def acceptable_args(self, _to, _from):
        _other = {}
        # If the method has a variable called 'args'
        # then assign all the arguments to 'args'
        if 'args' in _to:
            _to['args'] = _from
            return (_to, {})

        # Collect arguments that will not
        # be passed into the method
        for key, value in _from.items():
            if key not in _to:
                _other[key] = _from[key]

        # Collect arguments that will be
        # passed to the method
        for key, value in _to.items():
            if key in _from:
                _to[key] = _from[key]
            # Remove arguments that have no value this allows
            # default values on the method signature to take effect
            if _to[key] is None:
                del _to[key]
        return (_to, _other)


class MethodWrapper(SubCommand):

    def __init__(self, cmd, method):
        # Copy over all the attr of the cmd class
        # since we are taking it's place
        for name in dir(self):
            if name.startswith('__'):
                continue
            setattr(self, name, getattr(cmd, name))
        # Overide the commands, since we only
        # want to execute 1 method
        self._commands = method

    def bash_completion(self):
        return 0

    def __call__(self, args, prog):
        """
        Figure out which command for this sub-command should be run
        then pass the arguments to the commands parser
        """
        self.prog = prog
        return self.call_method(args, self._commands)
