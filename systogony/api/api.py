"""

"""
import json
import logging
import os
import socket

from collections import defaultdict
from functools import cached_property

from ..environment import Environment


log = logging.getLogger('systogony')


class ApiInterface:

    def __init__(self, config):

        self.config = config


    def get_cache(self, structure):

        if self.config['force_cache_regen'] or not self.config['use_cache']:
            log.debug(f"Skipping cache load, as configured")
            return None

        cache_path = os.path.join(
            self.config['blueprint_path'], f".cache-{structure}.json"
        )
        if not os.path.exists(cache_path):
            log.debug(f"No cache for {structure}, generating new")
            return False

        cache_timestamp = os.path.getmtime(cache_path)
        for root, dirs, files in os.walk(self.config['blueprint_path']):
            for fname in files:
                path = os.path.join(root, fname)
                if os.path.getmtime(path) > cache_timestamp:
                    log.debug(
                        f"Updated blueprint {fname}, "
                        + f"regenerating {structure} cache"
                    )
                    return False

        with open(cache_path) as fh:
            cache = fh.read()
        try:
            cache = json.loads(cache)
            log.info("No updates to blueprint, using cache")
        except json.decoder.JSONDecodeError:
            log.info("Cache failed to load, regenerating")
            return False

    def write_cache(self, data, structure):

        if not self.config['use_cache']:
            return None

        cache_path = os.path.join(
            self.config['blueprint_path'], f".cache-{structure}.json"
        )
        with open(cache_path, 'w') as fh:
            json.dump(data, fh, indent=4)

        log.info(f"Cache written to {cache_path}")

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
