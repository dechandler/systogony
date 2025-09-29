
import logging
import re
import sys

from subprocess import Popen, PIPE

log = logging.getLogger('systogony')

ANSI_ESCAPE = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')


class CliInterface:

    def __init__(self, config):

        log.debug(f"Initializing {str(self.__class__)}")

        self.config = config

        self.operations = {}

        self.no_args_operation = 'help'
        self.no_matching_args_operation = 'print'

        self.help_message = ""


    def handle_args(self, args):
        """
        Identify and execute the handler for the chosen operation

        """
        # Provide implicit help option
        self.operations['help'] = (
            self.operations.get('help')
            or {'handler': self.print_help}
        )

        # Index operations to include aliases
        subcommands = {}
        for name, op in self.operations.items():
            for op_name in op.get('aliases', []) + [name]:
                subcommands[op_name] = {
                    'name': name,
                    'handler': op['handler']
                }
        log.debug(f"Operation aliases:")
        for op_name, subcommand in subcommands.items():
            log.debug(f"    {op_name}: {subcommand['name']}")

        # If there are no arguments, use no_args_operation
        if not args:
            log.debug("No further arguments")
            log.debug(f"Defaulting to {self.no_args_operation}")
            args = [self.no_args_operation]

        # If no subcommands match the first arg, use no_matching_args_operation
        if args[0] not in subcommands:
            log.debug(f"Next arg exists but is not a valid operaion: {args[0]}")
            log.debug(f"Defaulting to {self.no_matching_args_operation}")
            args.insert(0, self.no_matching_args_operation)

        # Remove operation from args and identify handler
        selection = subcommands[args.pop(0)]
        name, handler = selection['name'], selection['handler']
        log.info(f"{str(self.__class__)} -> {name} with args: {args})")

        # Run lambda handlers to initialize the object
        # and get the .handle_args() method 
        if handler.__name__ == "<lambda>":
            handler = handler()

        # Run handler, passing on the remaining args
        handler(args)


    def run_command(self, cmd, cwd):
        """
        Utility method for running OS commands

        """
        log.info(f"Running command from {cwd}: {' '.join(cmd)}")

        p = Popen(cmd, cwd=cwd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

        while p.stdout.readable():
            line = p.stdout.readline()
            if not line:
                break

            err_line = p.stderr.readline()
            if err_line:
                print(err_line.decode(), file=sys.stderr, end='')

            log.debug(ANSI_ESCAPE.sub('', line.decode().rstrip()))
            print(line.decode(), end='')

        while p.stderr.readable():
            err_line = p.stderr.readline()
            if not err_line:
                break
            log.debug(ANSI_ESCAPE.sub('', err_line.decode().rstrip()))
            print(err_line.decode(), file=sys.stderr, end='')


    def print_help(self, args):
        """
        Print a predefined or generated help message
        for the operation

        """
        # Custom help message
        if self.help_message:
            print(self.help_message)
            return

        # Default help message is constructed from self.operations
        for name, operation in self.operations.items():
            print(f"  {name}:  {operation.get('help')}")
