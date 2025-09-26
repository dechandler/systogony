
import logging


log = logging.getLogger('systogony')


class CliInterface:

    help_message = "TODO: Make Help"
    no_args_operation = 'help'
    no_matching_args_operation = 'print'
    operations = {}


    def handle_args(self, args):

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
        log.debug(f"Subcommand aliases:")
        for op_name, subcommand in subcommands.items():
            log.debug(f"    {op_name}: {subcommand['name']}")

        # If there are no arguments, use no_args_operation
        if not args:
            args = [self.no_args_operation]

        # If no subcommands match the first arg, use no_matching_args_operation
        if args[0] not in subcommands:
            args.insert(0, self.no_matching_args_operation)

        # Finalize the operation and remove it from args
        self.op_name = args.pop(0)

        log.debug(f"Subcommand {self.op_name} with args: {args}")

        # Identify the handler to use
        handler = subcommands[self.op_name]['handler']

        # Run lambda handlers to initialize the object
        # and get the .handle_args() method 
        if handler.__name__ == "<lambda>":
            handler = handler()

        # Run handler, passing on the remaining args
        handler(args)


    def print_help(self, args):

        print(self.help_message)
