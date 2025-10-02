"""


"""
import json
import logging

from ..exceptions import (
    BlueprintLoaderError,
    NonMatchingPathSignal,
    MissingServiceError,
    NotReadySignal
)

log = logging.getLogger("systogony")


class ResourceShorthandQuery:

    def __init__(self, config, environment):

        self.config = config
        self.env = environment


    def resolve_to_rtype(
        self, shorthand, source_rtype_priorities, target_rtype
    ):
        """
        shorthand:
        source_rtype_priorities: list of resource types to match with shorthand
        target_rtype: for each matching resource, return associated resources
                      matching resource type target_rtype

        """

        rtype, matches = self.get_priority_matches(
            shorthand, source_rtype_priorities
        )

        if not matches:
            raise BlueprintLoaderError(f"No matches for shorthand: {shorthand}")
        
        # Since each resource object has its connections to each other object
        # type enumerated, we can query for the requested resource type
        targets = {}
        for match in matches:
            log.debug(f"Getting {target_rtype} for {match.fqn}")
            match_rtypes = match.__getattribute__(target_rtype)
            log.debug(f"    {match_rtypes}")
            targets.update(match_rtypes)

        return targets


    def get_priority_matches(self, shorthand, rtype_priorities):
        """

        """
        sorted_matches = { rtype: [] for rtype in rtype_priorities }

        matches = self.walk_get_matches(
            shorthand, resource_types=rtype_priorities
        )
        for match in matches.values():
            sorted_matches[match.resource_type].append(match)

        for rtype in rtype_priorities:
            if sorted_matches[rtype]:
                return rtype, sorted_matches[rtype]

        return None, []



    def walk_get_matches(self, shorthand_str, resource_types=None):


        if resource_types is None:
            resource_types = [
                'network', 'service', 'host', 'interface', 'service_instance'
            ]
        # names_out = {
        #     name: [
        #         r.serialized
        #         for r in resources
        #     ]
        #     for name, resources in self.names.items()
        # }
        log.debug(f"Shorthand Lookup (walk_get_matches):")
        log.debug(f"  Shorthand: {shorthand_str}")
        log.debug(f"  Resource types: {str(resource_types)}")
        #log.debug(f"    Names: {json.dumps(names_out, indent=4)}")

        shorthand = shorthand_str.split('.')
        name = shorthand[-1]
        try:
            possible_matches = self.env.names[name]
        except KeyError:
            raise BlueprintLoaderError(f"No resource matching {shorthand_str}")

        matches = {}
        for possible_match in possible_matches:
            log.debug(f"  Testing match: {str(possible_match.fqn)}")
            try:
                new_matches = possible_match.walk_matches(shorthand, resource_types)
            except NonMatchingPathSignal:
                continue
            matches.update({
                str(match.fqn): match for match in new_matches.values()
            })
        log.debug(f"Matches: {json.dumps([str(match.fqn) for match in matches.values()])}")
        return matches
