"""


"""
import json
import logging
import os
import yaml

from ..exceptions import (
    BlueprintLoaderError
    # NonMatchingPathSignal,
    # MissingServiceError,
    # NotReadySignal
)

log = logging.getLogger("systogony")

class Blueprint:

    def __init__(self, config):

        self.config = config    
        self.blueprint = self.load_blueprint(config['blueprint_path'])

    def __getitem__(self, key):
        return self.blueprint[key]


    def load_blueprint(self, bp_dir):

        blueprint = {
            'hosts': {},
            'networks': {},
            'services': {}, 
            'vars': {}
        }
        # Load and consolidate blueprint data from files and subdirs
        bp_dir = os.path.expanduser(bp_dir)
        log.debug(f"Loading blueprint data from {bp_dir}")
        for component, spec in blueprint.items():

            # Generate list of file paths for current blueprint component
            paths = []
            main_file = os.path.join(bp_dir, f"{component}.yaml")
            if os.path.isfile(main_file):
                paths.append(main_file)
            bp_subdir = os.path.join(bp_dir, component)
            if os.path.isdir(bp_subdir):
                for fname in sorted(os.listdir(bp_subdir)):
                    if fname.endswith(".yaml"):
                        paths.append(os.path.join(bp_subdir, fname))

            # Load data from discovered files
            for path in paths:

                try:
                    with open(path) as fh:
                        data = yaml.safe_load(fh)
                except Exception as e: #(
                #         KeyError, TypeError, UnicodeDecodeError,
                #         yaml.scanner.ScannerError, yaml.parser.ParserError
                # ):
                    log.warning(f"YAML parse failure, ignoring: {path}")
                    continue

                log.debug(f"{component} data loaded from {path}:")
                log.debug(json.dumps(data, indent=4))

                # Update component data, but update
                # top-level dictionaries, rather
                # than overwriting
                for conf_key, conf_data in data.items():
                    if type(spec.get(conf_key)) is type(conf_data) is dict:
                        spec[conf_key].update(conf_data)
                    else:
                        spec[conf_key] = conf_data

        return blueprint
