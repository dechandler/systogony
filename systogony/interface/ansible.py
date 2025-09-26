"""



"""
import logging
import os
import re
import sys

from subprocess import Popen, PIPE

from .cli import CliInterface

log = logging.getLogger("systogony")


class AnsibleCli(CliInterface):


    def __init__(self, config):

        log.debug("Initializing AnsibleCli")

        self.config = config

        self.operations = {
            'ansible-playbook': {
                'aliases': ['run'],
                'handler': self.run_playbook
            }

        }
        self.no_args_operation = 'help'
        self.no_matching_args_operation = 'run'

    def run_playbook(self, args):

        log.debug(f"AnsibleCli.run_playbook(args={args})")

        cmd = [
            "ansible-playbook", "-i", os.path.abspath(sys.argv[0])
        ]

        if self.config['ask_become_pass']:
            cmd.append('-K')

        if self.config['ask_vault_pass']:
            cmd.append('--ask-vault-pass')

        cmd.extend(args)

        log.info(' '.join([
            f"Running Ansible command from {self.config['ansible_dir']}:",
            ' '.join(cmd)
        ]))

        ansi_escape = re.compile(
            r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]'
        )

        p = Popen(
            cmd,
            cwd=self.config['ansible_dir'],
            stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        while p.stdout.readable():
            line = p.stdout.readline()
            if not line:
                break
            log.debug(ansi_escape.sub('', line.decode().rstrip()))
            print(line.decode(), end='')
