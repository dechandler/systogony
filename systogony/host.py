
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
        # Prioritize claims on host, then which network,
        default_claims = {'hosts': [], 'net': []}
        for iface in self.interfaces.values():
            if 'default' in iface.spec:
                default_claims['hosts'].append(iface)
            if iface.network.claims_default or len(self.interfaces) == 1:
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
        mounts.extend(self.spec.get('mounts', []))
        for inst in self.service_instances.values():
            mounts.extend(inst.spec.get('mounts', []))

        return mounts

    @property
    def firewall_rules(self):

        rules = {}
        for iface in self.interfaces.values():
            rules.update(iface.firewall_rules)
        log.debug("Firewall Rules")
        log.debug(rules)
        return rules


    @property
    def extra_vars(self):

        # rules = {}
        # for net_fqn, net_rules in self.firewall_rules.items():
        #     net_name = self.env.networks[net_fqn].name
        #     rules[net_name] = {}
        #     for rule_type, typed_rules in net_rules.items():
        #         rules[net_name][rule_type] = []
        #         for acl_fqn, rule in typed_rules.items():
        #             log.debug(rule)
        #             rules[net_name][rule_type].append(rule)

            #     rules[str(net_fqn)][rule_type]



        extra_vars = {
            'service_instances': {
                inst.name: inst.vars
                for inst in self.service_instances.values()
            },
            'network_interfaces': {
                net_name: iface.vars
                for net_name, iface in self.interfaces.items()
            },
            'mounts': self.mounts,
            #'rules': rules
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
            log.warning(
                f"Unknown default interface for {self.name}: \n"
                f"Default claims: {default_claims}"
            )
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

        # Determine immediate parent network of interface
        for net_fqn, net in self.env.networks.items():

            # Skip if top level network doesn't match
            if net_fqn[0] != ("network", iface_net_name):
                continue

            # Network name matching the host name means
            # it's an isolated subnet the host goes into
            if net_fqn[-1] == ("network", self.name):  # isolated subnet
                iface_parent_net = net
                break
        else:
            # Parent net is 
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
        # self.acls_ingress = {}
        # self.acls_egress = {}
        # self.acls = {'ingress': self.acls_ingress, 'egress': self.acls_egress}

        self.spec_var_ignores.extend(['groups', 'network'])
        # self.extra_vars = {}  # default

        #network = self.spec['network']
        #print(network, host.fqn)


        log.debug(f"    Interface data: {json.dumps(self.serialized, indent=4)}")

    def _get_xgress_ips(self, rule_type, remotes, network):

        ips = []
        for target in remotes.values():
            for net_fqn, addrs in target.addresses.items():
                log.debug(f"addrs: {target.name} {net_fqn} {addrs}")
                if net_fqn == self.network.network.fqn:
                    ips.extend(addrs)

        log.debug(f"IPs for {self.name}: {ips}")
        return ips





    @property
    def firewall_rules(self):

        rules = {
            'ingress': {},
            'egress': {},
            'forward': {}
        }
        get_rule = lambda acl: {
            'ports': acl.ports,
            'name': acl.name,
            'description': acl.description
        }

        # Ingress rules (INPUT)
        for acl in self.acls['ingress'].values():
            rule = get_rule(acl)
            rule['source_addrs'] = list(set(self._get_xgress_ips(
                'ingress', acl.sources, self.network.network
            )))
            rules['ingress'][acl.fqn] = rule

        # Egress rules (OUTPUT)
        for acl in self.acls['egress'].values():
            rule = get_rule(acl)
            rule['destination_addrs'] = list(set(self._get_xgress_ips(
                'egress', acl.sources, self.network.network
            )))
            rules['egress'][acl.fqn] = rule

        # Return rules if no router service
        for inst in self.service_instances.values():
            if inst.service.name == "router":
                break
        else:
            log.debug(rules)
            return {self.network.network.fqn: rules}

        # Forward rules (FORWARD)
        forward_acls = self.network.network.acls['forward']
        for acl in forward_acls.values():
            rule = {
                'name': acl.name,
                'description': acl.description,
                'ports': acl.ports,
                'source_addrs': [],
                'destination_addrs': []
            }

            net_fqn = self.network.network.fqn

            for src in acl.sources.values():
                rule['source_addrs'].extend(src.addresses.get(net_fqn, []))
            for dest in acl.destinations.values():
                rule['destination_addrs'].extend(dest.addresses.get(net_fqn, []))

            # Dedupe
            rule['source_addrs'] = list(set(rule['source_addrs']))
            rule['destination_addrs'] = list(set(rule['destination_addrs']))

            rules['forward'][acl.fqn] = rule

        log.debug(rules)
        return {self.network.network.fqn: rules}


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

    @property
    def addresses(self):

        if 'ip' not in self.spec:
            log.debug(f"Addresses requested, ip missing from spec, spec is {self.spec}")
            return {self.network.network.fqn: []}

        log.debug(f"{self.network.network.fqn}: {[str(self.spec['ip'])]}")
        return {self.network.network.fqn: [str(self.spec['ip'])]}

    @property
    def extra_vars(self):

        fw_rules = {}

        for rule_type, typed_rules in self.firewall_rules[self.network.network.fqn].items():
            fw_rules[rule_type] = []
            log.debug(typed_rules)
            for rule in typed_rules.values():
                # log.debug("STUFF")
                # log.debug(rule)
                fw_rules[rule_type].append(rule)

        extra_vars = {}
        if 'ip' in self.spec:
            extra_vars['ip'] = f"{self.spec['ip']}"
        if 'domain' in self.network.network.spec:
            extra_vars['fqdn'] = f"{self.host.name}.{self.network.network.spec['domain']}"
        extra_vars.update({
            'net_name': self.network.network.name,
            'default': self.is_default_iface,
            'firewall_rules': fw_rules
        })
        return extra_vars

    def _get_extra_serial_data(self):

        data = {}
        if 'ip' in self.spec:
            data['ip'] = f"{self.spec['ip']}"

        return data
