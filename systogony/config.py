

import json
import logging
import os

import yaml

log = logging.getLogger("systogony")


class SystogonyConfig:

    def __init__(self):

        self.config = self.get_config()
        self.configure_loggers()

    def get_config(self):

        """
        Set a default config, then load a config file

        The priority order is:
            Environment variable: SYSTOGONY_CONFIG (~ accepted)
            $HOME/.config/systogony/config.yaml

        """

        # Set defaults
        config = {
            'blueprint_path': os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../blueprints/demo")
            ),
            'ansible_dir': os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../ansible")
            ),
            'log_dir': "~/.config/systogony/log",
            'log_level': "warning",
            'inventory_tmp_file': "~/.config/systogony/.inventory.json",
            'ask_become_pass': True,
            'ask_vault_pass': False
        }

        # Override defaults with options from first existing file
        search_paths = [
            os.environ.get("SYSTOGONY_CONFIG", ""),
            "~/.config/systogony/config.yaml"
        ]
        for path_var in search_paths:
            path = os.path.expanduser(path_var)
            try:
                with open(path) as fh:
                    data = yaml.safe_load(fh)
                    config.update(data)
                    log.info(f"Config Path: {path}")
                self.path = path
                break
            except FileNotFoundError:
                pass
            except yaml.scanner.ScannerError:
                log.error(f"File exists at {path} but is not YAML parseable, aborting...")
                sys.exit(1)
            except Exception as e:
                log.debug(' '.join([
                    "Unexpected exception while loading",
                    f"yaml at {path}: ({e.__class__}) {e}"
                ]))

        config['log_dir'] = os.path.expanduser(config['log_dir'])

        log.debug(f"Loaded config: {json.dumps(config)}")

        return config


    def configure_loggers(self):

        os.makedirs(self.config['log_dir'], exist_ok=True)

        datefmt = "%Y-%m-%d_%H:%M:%S"
        log.setLevel(getattr(logging, self.config['log_level'].upper()))

        handler = logging.FileHandler(
            os.path.join(self.config['log_dir'], "systogony.log")
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)-7s %(message)s', datefmt=datefmt
        ))
        log.addHandler(handler)


    def items(self):

        return self.config.items()

    def __getitem__(self, key):

        return self.config.get(key)

    def __setitem__(self, key, value):

        self.config[key] = value
