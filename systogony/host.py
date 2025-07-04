
import ipaddress
import json
import logging

from collections import defaultdict
from functools import cached_property

from .resource import Resource
from .exceptions import BlueprintLoaderError


log = logging.getLogger("systogony")


class Host(Resource):




    def __init__(self, env, host_spec):

        log.debug(f"New Host - spec: {json.dumps(host_spec)}")

        self.resource_type = "host"
        self.shorthand_type_matches = [
            "host", "machine", "system", "server", "device", "dev"
        ]
        super().__init__(env, host_spec)

        # Associated resources by type
        self.hosts = {self.fqn: self}
        self.interfaces = {}  # registrar
        # self.networks  # property - interfaces -> network
        # self.services  # property - service_instances -> services
        self.service_instances = {}  # registrar

        # Lineage for walking up and down the heirarchy
        self.parent = None
        #self.children = {k: v for k, v in self.interfaces.items()}

        # Other attributes
        self.groups = host_spec.get('groups', [])
        if "os" in host_spec:
            self.groups.append(host_spec['os'])
        if "device" in host_spec:
            self.groups.append(host_spec['device'])

        self.spec_var_ignores.extend(['groups'])
        # self.extra_vars = {}  # default

        log.debug(f"Host data: {json.dumps(self.serialized, indent=4)}")


    @property
    def default_iface(self):

        # Record claims to being default interface
        default_claims = {'hosts': [], 'net': []}
        for iface in self.interfaces.values():
            if 'default' in iface.spec:
                default_claims['hosts'].append(iface)
            if iface.network.claims_default:
                default_claims['net'].append(iface)


        # Evaluate equally-prioritized claims to default interface
        # Error if ambiguous
        def select_claim(claims):
            if not claims:
                return None

            if len(claims) == 1:
                return claims[0]

            if len(claims > 1):
                raise BlueprintLoaderError(' '.join([
                    "Ambiguous default interface for",
                    f"{self.name}: {claims}"
                ]))

        # Prioritize claims to default interface
        default = (
            select_claim(default_claims['hosts'])
            or select_claim(default_claims['net'])
        )
        if not default:
            raise BlueprintLoaderError(
                f"Unknown default interface for {self.name}"
            )

        for iface in self.interfaces.values():
            iface.is_default_iface = True if iface == default else False
        
        return default


    @property
    def networks(self):



        return {
            iface.network.fqn: iface.network
            for iface in self.interfaces.values()
        }

    @property
    def services(self):

        return {
            inst.service.fqn: inst.service
            for inst in self.service_instances.values()
        }


    @cached_property
    def mounts(self):

        mounts = []
        for inst in self.service_instances.values():
            if 'mounts' in inst.spec:
                mounts.extend(inst.spec['mounts'])

        return mounts


    @cached_property
    def extra_vars(self):

        extra_vars = {
            'service_instances': {
                inst.name: inst.vars
                for inst in self.service_instances.values()
            },
            'network_interfaces': {
                iface.name: iface.vars
                for iface in self.interfaces.values()
            },
            'mounts': self.mounts
        }



        return extra_vars


    def add_interfaces(self):

        log.debug(f"Iface Specs for {self.name}: {self.spec.get('interfaces', {})}")

        # Create and register interfaces
        for iface_net_name, iface_spec in self.spec.get('interfaces', {}).items():
            log.debug(f"Iface Net Name: {iface_net_name}")
            log.debug(f"Iface Spec: {json.dumps(iface_spec)}")
            self._add_interface(iface_net_name, iface_spec=iface_spec)

        # Record claims to being default interface
        default_claims = {'hosts': [], 'net': []}
        for iface in self.interfaces.values():
            if 'default' in iface.spec:
                default_claims['hosts'].append(iface)
            if iface.network.claims_default:
                default_claims['net'].append(iface)

        # Evaluate equally-prioritized claims to default interface
        # Error if ambiguous
        def select_claim(claims):
            if not claims:
                return None

            if len(claims) == 1:
                return claims[0]

            if len(claims > 1):
                raise BlueprintLoaderError(' '.join([
                    "Ambiguous default interface for",
                    f"{self.name}: {claims}"
                ]))

        # Prioritize claims to default interface
        default = (
            select_claim(default_claims['hosts'])
            or select_claim(default_claims['net'])
        )
        if not default:
            raise BlueprintLoaderError(
                f"Unknown default interface for {self.name}"
            )

        for iface in self.interfaces.values():
            iface.is_default_iface = True if iface == default else False

        log.info(' '.join([
            f"Interfaces on {self.name}:",
            ', '.join([ iface.name for iface in self.interfaces.values() ])
        ]))


    def _add_interface(self, iface_net_name, iface_spec=None):

        log.debug(f"Adding interface: {iface_net_name} - {iface_spec}")
        iface_spec = iface_spec or {}
        iface_spec['name'] = f"{iface_net_name}.{self.name}"
        iface_spec['network'] = (('network', iface_net_name),)
        if iface_spec['network'] not in self.env.networks:
            raise BlueprintLoaderError(f"No network {iface_net_name} available for {self.name}")

        for net_fqn, net in self.env.networks.items():
            #print(net_fqn, iface_net_name)
            if net_fqn[0] != ("network", iface_net_name):
                continue
            if net_fqn[-1] == ("network", self.name):  # isolated subnet
                iface_parent_net = net
                break
        else:
            iface_parent_net = self.env.networks[iface_spec['network']]


        #iface_spec['network'] = networks[iface_net_name]
        #self.interfaces[(('iface', iface_net_name),)] = 
        Interface(
            self.env, iface_spec, iface_parent_net, self
        )


    def _get_extra_serial_data(self):

        return {
            'interfaces': {
                str(iface.fqn): iface.serialized
                for iface in self.interfaces.values()
            }, #self._fqn_str_list(self.interfaces),
            'service_instances': [
                str(fqn)
                for fqn in self.service_instances
                #for inst in inst_list
            ]
        }



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
        for acl in all_acls.values():
            acl_iface_fqns = [
                fqn for fqn, interface in self.interfaces.items()
                if acl.fqn in interface.acls['ingress']
            ]
            #if acl.fqn in 

        interfaces = {}


            # iface = interfaces[interface.fqn] = interface


            #     rule = {
            #         ''
            #         'interfaces': {
            #             fqn: iface
            #             for fqn, iface in self.interfaces.items()
            #             if fqn in interfaces
            #         },
            #         'sources': acl.sources,
            #         'ports': acl. acl.ports
            #     }

        if len(interfaces) == len(self.interfaces):
            pass

        # if host_fqn in [
        #     iface.host.fqn for iface in self.destinations.values()
        # ]:
        #     rule_type = "ingress"
        # elif host_fqn in [
        #     iface.host.fqn for iface in self.sources.values()
        # ]:
        #     rule_type = "egress"
        # elif self.env.hosts[host_fqn].network.router.fqn == host_fqn
        #     rule_type = "forward"

        rule = {
            'interfaces': {
                iface for fqn, iface in self.interfaces.items()
                if fqn in host.interfaces
            },
            'sources': self.sources,
            #'destinations': 
            'ports': self.ports
        }
        if target_type == "ingress":
            return {
                'interfaces': {
                    iface for fqn, iface in self.interfaces.items()
                    if fqn in host.interfaces
                },
                'sources': self.sources,
                'ports': self.ports
            }




    def fw_allow_service(self, service, sources, iface=None):



        for inst in self.service_instances.values():

            acl = Acl(
                matches,  # sources
                [self],  # destinations
                acl_spec.get('ports', {}),
                acl_spec.get('fw_log_count')
            )

class Interface(Resource):





    def __init__(self, env, iface_spec, network, host):

        log.debug("New Interface")
        log.debug(f"    Network: {network.fqn}")
        log.debug(f"    Host:    {host.fqn}")

        self.resource_type = "interface"
        self.shorthand_type_matches = [
            "interface", "iface",
            "host-interface", "host_interface", "host-iface", "host_iface",
            "net-interface", "net_interface", "net-iface", "net_iface" 
        ]

        super().__init__(env, iface_spec)

        self.fqn = tuple([*network.fqn, *host.fqn])

        self.network = network
        self.host = host
        if self.network.net_type == "isolated":
            net_cidr = ipaddress.ip_network(self.network.cidr)
            self.spec['ip'] = [*net_cidr.hosts()][1]

        # Register this resource
        log.debug(f"Registering to {self.host.name}: {network.network.fqn[0][1]}")
        host.interfaces[network.network.fqn[0][1]] = self
        network.interfaces[host.fqn] = self

        # Associated resources by type
        self.hosts = {self.host.fqn: self.host}  # static
        self.interfaces = {self.fqn: self}  # static
        self.networks = {self.network.fqn: self.network}  # static
        # self.services  # property via service_instances if self in host interfaces
        # self.service_instances   # property via host if self in host ifaces

        # Lineage for walking up and down the heirarchy
        self.parent = network

        # Other attributes
        self.acls_ingress = {}
        self.acls_egress = {}
        self.acls = {'ingress': self.acls_ingress, 'egress': self.acls_egress}

        self.spec_var_ignores.extend(['groups', 'network'])
        # self.extra_vars = {}  # default

        #network = self.spec['network']
        #print(network, host.fqn)


        log.debug(f"    Interface data: {json.dumps(self.serialized, indent=4)}")


    @property
    def services(self):

        return {
            inst.service.fqn: inst.service
            for inst in self.service_instances.values()
        }

    @property
    def service_instances(self):

        return {
            inst.fqn: inst
            for inst in self.host.service_instances.values()
            if self.fqn in [*inst.interfaces]
        }

    @cached_property
    def extra_vars(self):

        extra_vars = {}
        if 'ip' in self.spec:
            extra_vars['ip'] = f"{self.spec['ip']}"
        if 'domain' in self.network.network.spec:
            extra_vars['fqdn'] = f"{self.host.name}.{self.network.network.spec['domain']}"
        extra_vars.update({
            'net_name': self.network.network.name,
            'default': self.is_default_iface
        })
        return extra_vars

    def _get_extra_serial_data(self):

        data = {}
        if 'ip' in self.spec:
            data['ip'] = f"{self.spec['ip']}"

        return data
