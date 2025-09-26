
import sys

from .config import SystogonyConfig
from .interface import MainCli


from .exceptions import (
    BlueprintLoaderError, MissingServiceError
)

def main():

    config = SystogonyConfig()

    try:
        MainCli(config).handle_args(sys.argv[1:])

    except BlueprintLoaderError:
        pass
    except MissingServiceError:
        pass

    except KeyboardInterrupt:
        pass