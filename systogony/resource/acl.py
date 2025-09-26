"""


"""
import json
import logging


from .resource import Resource



log = logging.getLogger("systogony")


class Acl(Resource):
    """
    Called from SystogonyEnvironment.get_acls()

    """
    def __init__(self, env, origin, acl_spec, sources, destinations):
        """


        """

        log.debug(f"New Acl {acl_spec['name']}")

        self.resource_type = "acl"
        self.shorthand_type_matches = [
            "acl"
        ]
        super().__init__(env, acl_spec)

        self.origin = origin
        self.sources = sources or {}
        self.sources_spec = acl_spec['source_specs']
        self.destinations = destinations or {}
        self.destinations_spec = acl_spec['destination_specs']
        self.ports = acl_spec['ports']
        self.networks = {
            iface.network.network.fqn: iface.network.network
            for iface in origin.interfaces.values()
        }

        # Register this resource
        origin.acls['owned'][self.fqn] = self
        for src in sources.values():
            for iface in src.interfaces.values():
                iface.acls['egress'][self.fqn] = self
            #src.acls['egress'][self.fqn] = self
        for dest in destinations.values():
            for iface in dest.interfaces.values():
                iface.acls['ingress'][self.fqn] = self
            #dest.acls['ingress'][self.fqn] = self

        for network in self.networks.values():
            #for iface in 
            network.acls['forward'][self.fqn] = self


        for rule_type in ["ingress", "egress"]:
            # get and dedupe networks the acl is attached to
            self.networks.update(self._register_to_interfaces(rule_type))
        for network in self.networks.values():
            network.acls['forward'][self.fqn] = self


        # Associated resources by type
        self.interfaces = {**self.sources, **self.destinations}  # static

        # Other attributes
        self.description = acl_spec['description']
        self.does_count = acl_spec.get('does_count', False)

        # self.spec_var_ignores.extend([])
        # self.extra_vars = {}  # default

        log.debug(f"    description: {self.description}")
        log.debug(f"    sources: {json.dumps([str(k) for k in self.sources])}")
        log.debug(f"    dests: {json.dumps([str(k) for k in self.destinations])}")


        # Lineage for walking up and down the heirarchy


    # def get_rules(self, networks, rule_type):


    #     for net_fqn, net in networks.items():
    #         if net_fqn not in self.networks:
    #             continue
    #         rule = {
    #             'network': net,
    #             'ports': self.ports
    #         }
    #         if rule_type == "ingress":
    #             rule['sources'] = self.sources
    #         elif rule_type == "egress":
    #             rule['destinations'] = self.destinations


    # def get_ingress_rules(self, networks):

    #     #

    #     rules = []

    #     for net_fqn, net in networks.items():
    #         if net_fqn not in self.networks:
    #             continue
    #         rule = {
    #             'network': net,
    #             'sources': self.sources,
    #             'ports': self.ports

    #         }



    # def get_ingress_rules(self):

    #     self.rules = {}

    #     ingress_acls = {}

    #     # where all host interfaces have an acl, set rule interface to None
    #     acls = defaultdict(dict)
    #     for interface in self.interfaces.values():
    #         for acl_fqn, acl in interface.acls['ingress'].items():
    #             if acl_fqn not in acls:
    #                 acls[acl_fqn] = {'object': acl, 'interfaces': {}}
    #             acls[acl_fqn]['interfaces'][interface.fqn] = interface

    #     rules = []
    #     for acl_data in acls.values():
    #         rule = {}
    #         if len(acl_data['interfaces']) != len(self.interfaces):
    #             rule['interfaces'] = self.interfaces

    #         acl = acl_data['object']


    #         rules.append(rule)

    def _register_to_interfaces(self, rule_type):

        targets = self.sources if rule_type == "ingress" else self.destinations

        networks = {}  # get and dedupe networks the acl is attached to
        for target in targets.values():
            for host in target.hosts.values():
                for iface in host.interfaces.values():
                    if (
                        iface.fqn not in target.interfaces
                        or iface.network.network.fqn not in self.networks
                    ):
                        continue
                    log.debug(f"    register {rule_type} to {iface.fqn}: {self.name}")
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

