
import logging

from functools import cached_property

from .exceptions import NonMatchingPathSignal

log = logging.getLogger("systogony")


class Resource:

    def __init__(self, env, spec):

        self.env = env
        self.spec = spec

        self.name = spec['name']



        #self.env.names[self.name].append(self)

        self.fqn = tuple([(self.resource_type, spec['name'])])
        #self.fqn = tuple([*parent.fqn, fqn] if parent else [fqn])

        # Register 
        self.env.register(self)

        # Shortcut to associated resources by type
        # self.hosts = {self.host.fqn: self.host}
        # self.interfaces = {self.fqn: self}
        # self.networks = {network.fqn: network}
        # self.services = {}  # connected via service_instances


        self.spec_var_ignores = [
            'hosts', 'interfaces', 'allows', 'access', 'restrictions', 'name'
        ]
        #self.extra_vars = {}

        self.parent = None
        self.children = {}
        self.network = None
        self.ports = None
        self.rules = {'input': [], 'output': [], 'forward': []}


        self.parents = []


    @property
    def serialized(self):

        attrs = {
            'name': self.name,
            'fqn': str(self.fqn),
            'resource_type': self.resource_type
        }

        if self.network:
            attrs['network'] = str(self.network.fqn)
        #attrs['parent'] = str(self.parent.fqn) if self.parent else None

        attrs.update(self._get_extra_serial_data())

        return attrs

    def __gt__(self, other):
        return self.name > other.name
    def __lt__(self, other):
        return self.name < other.name
    def __ge__(self, other):
        return self.name >= other.name
    def __le__(self, other):
        return self.name <= other.name


    def _get_extra_serial_data(self):
        return {}

    def _fqn_str_list(self, resources_dict):

        return [ str(resource.fqn) for resource in resources_dict.values() ]


    def _fqns_strs(self, targets):

        items = []
        for target in targets:
            target_items = []
            for pair in target:
                target_items.extend(pair)
            items.append('.'.join(target_items))
        return items

    @property
    def short_fqn_str(self):

        return '-'.join([ pair[1] for pair in self.fqn ])

    @cached_property
    def vars(self):

        rvars = {
            k: v for k, v in self.spec.items() if k not in self.spec_var_ignores
        }
        rvars.update(self.extra_vars)
        return rvars

    @cached_property
    def extra_vars(self):
        return {}

    def gen_acls(self):

        for acl_spec_type in ['allows', 'access']:
            self._gen_acls_by_spec_type(acl_spec_type)

    def _gen_acls_by_spec_type(self, acl_spec_type):

        """
        acl types: 'allows', 'access'

        """

        if not self.spec.get(acl_spec_type):
            return

        matches = {}
        for shorthand, overrides in self.spec[acl_spec_type].items():
            matches.update({
                target.fqn: {
                    'target': target,
                    'overrides': {**(overrides or {})},
                }
                for target in self.env.walk_get_matches(shorthand).values()
            })

        owner = {self.fqn: self}
        owner_specs = {}
        targets = {
            fqn: target['target'] for fqn, target in matches.items()
        }
        target_specs = {
            fqn: matches[fqn].get('overrides') for fqn in targets
        }
        acl_spec = {}
        if acl_spec_type == "allows":
            sources, destinations = targets, owner
            acl_spec['source_specs'] = target_specs
            acl_spec['destination_specs'] = owner_specs
        elif acl_spec_type == "access":
            sources, destinations = owner, targets
            acl_spec['source_specs'] = owner_specs
            acl_spec['destination_specs'] = target_specs


        owner_str = '-'.join(self._fqns_strs([*owner]))
        targets_str = '-'.join(self._fqns_strs([*targets]))
        src_str = ', '.join(self._fqns_strs([*sources]))
        dest_str = ', '.join(self._fqns_strs([*destinations]))

        acl_spec.update({
            'name': "_".join([owner_str, acl_spec_type, targets_str]),
            'origin': self,
            'description': " ".join([
                f"{src_str} TO {dest_str} ON",
                str([*self.ports.values()]) if self.ports else "any port"
            ]),
            'ports': self.ports
        })

        self.env.gen_acl(acl_spec, sources, destinations)


    # def gen_defined_acls(self, ):




    #     acl_kwargs = {}
    #     {
    #         'description': 
    #         'sources':
    #         'destinations':
    #         'ports':
    #     }

    #     if 

    #         for dest in matches.values():
    #             if 'description' not in overrides:
    #                 overrides['description'] = 



    #             destinations[dest.fqn] = {
    #                 'target': dest,
    #                 'overrides': overrides,
    #                 'description': (
    #                     overrides.get('description')
    #                     or
    #                 ) 
    #             }

    #         description=f"{'.'.join(self.fqn)} access to {', '.join([destinations])}",
    #         sources={self.fqn: {'target': self, 'overrides': {}}},
    #         destinations=destinations,
    #         ports=self.ports



    # def get_access_acls(self, ):

    #     if not self.spec.get('access'):
    #         return

    #     fqn_str = lambda fqn, major, minor: major.join([
    #         minor.join(resource) for resource in fqn
    #     ])

    #     destinations = {}
    #     for shorthand, overrides in self.spec['access'].items():
    #         matches = self.env.walk_get_matches(shorthand)
    #         for dest in matches.values():
    #             if 'description' not in overrides:
    #                 overrides['description'] = 



    #             destinations[dest.fqn] = {
    #                 'target': dest,
    #                 'overrides': overrides,
    #                 'description': (
    #                     overrides.get('description')
    #                     or
    #                 ) 
    #             }


    #     name_str = fqn_str(self.fqn, '_', '-')
    #     desc_src_str = fqn_str(self.fqn, '.', '.')
    #     desc_dest_str = ', '.join([
    #         fqn_str(dest.fqn, '.', '.') for dest in destinations
    #     ])

    #     Acl(
    #         self.env, f"{name_str}_access",
    #         description=f"{'.'.join(self.fqn)} access to {', '.join([destinations])}",
    #         sources={self.fqn: {'target': self, 'overrides': {}}},
    #         destinations=destinations,
    #         ports=self.ports
    #     )

    # def get_(self):


    #     for parent in self.parents:



    def walk_matches(self, shorthand, resource_types=None):

        shorthand = [*shorthand]
        log.debug(f"    walk_matches")
        log.debug(f"        FQN: {str(self.fqn)}")
        log.debug(f"        Shorthand: {shorthand}")
        #log.debug(f"        Resource types: {str(resource_types)}")

        #print(shorthand, self.fqn, self.resource_type)

        if resource_types is None:
            resource_types = [
                'network', 'host', 'interface', 'service', 'service_instance'
            ]

        if shorthand and shorthand[-1] == self.fqn[-1][1]:
            log.debug(f"        Matches {shorthand[-1]}")
            if len(shorthand) == 1:
                log.debug(f"        Popping {shorthand[-1]}")
                shorthand.pop(-1)
            elif (
                len(shorthand) >= 2
                and shorthand[-2] in self.shorthand_type_matches
            ):  #== self.fqn[-1][0]:
                log.debug(f"        Popping {shorthand[-2]} {shorthand[-1]}")
                shorthand.pop(-1)
                shorthand.pop(-1)
            else:
                log.debug(f"        No matching shorthand type: {shorthand[-2]} not in {self.shorthand_type_matches}")

        matches = (
            {self.fqn: self} if self.resource_type in resource_types else {}
        )

        if not shorthand:  # This and all ancestors match
            for parent in self.parents:
                matches.update({
                    str(match.fqn): match
                    for match
                    in parent.walk_matches(shorthand, resource_types).values()
                })
            if matches:
                log.debug(f"    Returning matches: {matches}")
            return matches

        if not self.parents:  # Does not match, turn back
            # More shorthand remaining, but we've reached the top level
            log.debug(f"    Non-matching")
            log.debug(f"        Current object: {self.fqn}")
            log.debug(f"        Remaining shorthand: {shorthand}")
            raise NonMatchingPathSignal()

        # Still more to go
        for parent in self.parents:
            try:
                matches.update({
                    match.fqn: match
                    for match
                    in parent.walk_matches(shorthand, resource_types).values()
                })
            except NonMatchingPathSignal:
                continue

        if matches:
            log.debug(f"    Returning matches: {matches}")
        return matches


    def get_descendents(self, types=None):

        if types is None:
            types = [
                'networks', 'hosts', 'interfaces',
                'services', 'service_instances'
            ]
        descendents = []
        for child in self.children.values():
            descendents.append(child)
            descendents.extend(child.get_descendents(types))
        return descendents
