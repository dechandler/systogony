"""


"""
import json
import logging


from .resource import Resource



log = logging.getLogger("systogony-inventory")


class Acl(Resource):

    def __init__(self, env, acl_spec, sources, destinations):

        log.debug(f"New Acl {acl_spec['name']}")

        self.resource_type = "acl"
        self.shorthand_type_matches = [
            "acl"
        ]
        super().__init__(env, acl_spec)

        self.sources = sources
        self.sources_spec = acl_spec['source_specs']
        self.destinations = destinations
        self.destinations_spec = acl_spec['destination_specs']

        # Register this resource
        self.networks = {}  # static
        for rule_type in ["ingress", "egress"]:
            self.networks.update(self._register_to_interfaces(rule_type))
        for network in self.networks.values():
            network.acls['forward'][self.fqn] = self


        # Associated resources by type
        self.interfaces = {**self.sources, **self.destinations}  # static

        # Other attributes
        self.origin = acl_spec['origin']
        self.description = acl_spec['description']
        self.ports = acl_spec['ports']
        self.does_count = acl_spec.get('does_count', False)

        # self.spec_var_ignores.extend([])
        # self.extra_vars = {}  # default

        log.debug(f"    description: {self.description}")
        log.debug(f"    sources: {json.dumps([str(k) for k in self.sources])}")
        log.debug(f"    dests: {json.dumps([str(k) for k in self.destinations])}")


        # Lineage for walking up and down the heirarchy



    def _register_to_interfaces(self, rule_type):

        targets = self.sources if rule_type == "ingress" else self.destinations

        networks = {}  # get and dedupe networks the acl is attached to
        for target in targets.values():
            for host in target.hosts.values():
                for iface in host.interfaces.values():
                    if iface.fqn not in target.interfaces:
                        continue
                    log.debug(f"    register {rule_type}: {iface.fqn}")
                    networks[iface.network.fqn] = iface.network
                    iface.acls[rule_type][self.fqn] = self
                    #iface.__getattribute__(f'acls_{rule_type}')[self.fqn] = self
        return networks





    def _get_extra_serial_data(self):

        return {
            'destinations': {
                str(dest.fqn): dest.serialized
                for dest in self.destinations.values()
            },
            'sources': {
                str(src.fqn): src.serialized
                for src in self.sources.values()
            },
            'ports': self.ports
        }



class Rule(Resource):

    def __init__(self, env, rule_spec, acl, host):

        # if 'name' not in rule_spec:
        #     rule_spec['name'] = 

        log.debug(f"New Rule {rule_spec['name']}")

        self.resource_type = "rule"
        self.shorthand_type_matches = [
            "rule"
        ]
        super().__init__(env, rule_spec)

        self.acl = acl
        self.host = host

        # Associated resources by type
        self.hosts = {host.fqn: host}
        self.interfaces = {
            fqn: interface
            for fqn, interface in self.host.interfaces.items()
            if fqn in self.acl.sources
        }


        # self.networks  # property - interfaces -> network
        # self.services  # property - service_instances -> services
        self.service_instances = {}  # registrar

        # Lineage for walking up and down the heirarchy
        self.parent = None
        #self.children = {k: v for k, v in self.interfaces.items()}

        # Other attributes
        self.groups = host_spec.get('groups', [])

        self.spec_var_ignores.extend(['groups'])
        # self.extra_vars = {}  # default


        log.debug(f"Host data: {json.dumps(self.serialized, indent=4)}")


    def get_rule_type(self):

        pass





    def get_ingress_rules(self):

        self.rules = {}

        ingress_acls = {}

        # where all host interfaces have an acl, set rule interface to None
        acls = defaultdict(dict)
        for interface in self.interfaces.values():
            for acl_fqn, acl in interface.acls['ingress'].items():
                if acl_fqn not in acls:
                    acls[acl_fqn] = {'object': acl, 'interfaces': {}}
                acls[acl_fqn]['interfaces'][interface.fqn] = interface

        rules = []
        for acl_data in acls.values():
            rule = {}
            if len(acl_data['interfaces']) != len(self.interfaces):
                rule['interfaces'] = self.interfaces

            acl = acl_data['object']


            rules.append(rule)
