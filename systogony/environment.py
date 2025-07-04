
import json
import logging
import os

from collections import defaultdict
from functools import cached_property

import yaml

from .acls import Acl
from .host import Host, Interface
from .network import Network
from .services import Service, ServiceInstance

from .exceptions import BlueprintLoaderError, NonMatchingPathSignal


log = logging.getLogger("systogony")


class SystogonyEnvironment:

    def __init__(self, subdir):

        self.blueprint = self.load_blueprints(subdir)




        #self.resources = {}
        self.hosts = {}
        self.interfaces = {}
        self.networks = {}
        self.services = {}
        self.service_instances = {}

        self.acls = {}

        # Index of resources by base name
        self.names = defaultdict(list)


        # Create host objects
        self.host_groups = defaultdict(list)
        for host_name, host_spec in self.blueprint['hosts'].items():
            host_spec['name'] = host_name
            host = Host(self, host_spec)
            fqn = tuple(host.fqn)
            
            self.hosts[fqn] = host
            for group_name in host.groups:
                self.host_groups[group_name].append(host)

        for group_name, host_list in self.host_groups.items():
            self.host_groups[group_name] = sorted(host_list)

            # for iface in host.interfaces.values():

        # Generate WAN pseudo-network
        self.networks[(('network', 'wan'),)] = Network(
            self, {'name': "wan", 'type': "wan", 'cidr': "0.0.0.0/0"}
        )

        # Create top level network objects
        for net_name, net_spec in self.blueprint['networks'].items():
            net_spec['name'] = net_name
            net = Network(self, net_spec)
            self.networks[net.fqn] = net

            for subnet in net.get_descendents(types=['networks']):
                self.networks[subnet.fqn] = subnet



        # Generate interfaces to connect host to network
        for host in self.hosts.values():
            host.add_interfaces()


        """
        # Generate services
        for svc_name, svc_bp in self.blueprint['services'].items():
            svc_bp['name'] = svc_name
            self.services[svc_name] = Service(self, svc_bp)

        # Loop over services until all are resolved
        # since services can reference each other
        pass_num = 0
        max_passes = 10
        while pass_num < max_passes:
            pass_num += 1
            log.debug(f"Services populate hosts pass {pass_num}")

            for service in self.services.values():
                service.populate_hosts()

            for service in self.services.values():
                if not service.hosts_complete:
                    break
            else:  # Services are complete
                break
        else:
            # Hosts shorthand did not resolve for all service definitions
            # Could be malformed shorthand or circular definition
            raise(BlueprintLoaderError(' '.join([
                "Error loading service hosts:",
                json.dumps([
                    svc.fqn for svc in self.services.values()
                    if not svc.hosts_complete
                ])
            ])))
        """

        # Resolve shorthands in service allow/access
        # for service in self.services.values():
        #     service.apply_rules()


        # Generate acls
        # for resource in self.resources.values():
        #     resource.gen_acls()


    def __str__(self):

        out = {
            'networks': {
                str(k): net.serialized for k, net in self.networks.items()
            },
            'hosts': {
                str(k): host.serialized for k, host in self.hosts.items()
            },
            'services': {
                str(k): svc.serialized for k, svc in self.services.items()
            }
            #'names': self.names
        }
        #print(out)
        return json.dumps(out, indent=4)


    @cached_property
    def hostvars(self):

        env_hostvars = {
            host.name: host.vars
            for host in self.hosts.values()
        }
        env_hostvars.update({
            network.metahost_name: network.vars
            for network in self.networks.values()
            if network.net_type != "isolated"
        })

        return env_hostvars


    @cached_property
    def groups(self):
        """

        """
        groups = defaultdict(list)
        for host in self.hosts.values():
            for group in host.groups:
                groups[group].append(host.name)

        for network in self.networks.values():
            if network.net_type == "isolated":
                continue
            groups["network_metahost"].append(network.metahost_name)
            groups[f"net_{network.short_fqn_str}"] = [
                host.name for host in network.hosts.values()
            ]

        return groups


    def _get_group_for_network(self, network):

        name = f"net_{network.name}"
        hosts = []
        gvars = {'cidr': network.cidr}
        if network.rules['forward']:
            gvars['rules'] = network.rules

        return name, hosts, gvars


    @property
    def resources(self):

        return {
            **self.networks,
            **self.hosts,
            **self.interfaces,
            **self.services,
            **self.service_instances
        }

    def register(self, resource):

        self.names[resource.name].append(resource)
        self.resources[resource.fqn] = resource
        registries = {
            'host': self.hosts,
            'interface': self.interfaces,
            'network': self.networks,
            'service': self.services,
            'service_instance': self.service_instances,
            'acl': self.acls
        }
        registries[resource.resource_type][resource.fqn] = resource

    def gen_acl(self, acl_spec, sources, destinations):

        Acl(self, acl_spec, sources, destinations)


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
        
        targets = {}
        for match in matches:
            targets.update(match.__getattribute__(target_rtype))

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
        names_out = {
            name: [
                r.serialized
                for r in resources
            ]
            for name, resources in self.names.items()
        }
        log.debug(f"Shorthand Lookup (walk_get_matches):")
        log.debug(f"  Shorthand: {shorthand_str}")
        log.debug(f"  Resource types: {str(resource_types)}")
        #log.debug(f"    Names: {json.dumps(names_out, indent=4)}")

        shorthand = shorthand_str.split('.')
        name = shorthand[-1]
        try:
            possible_matches = self.names[name]
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


    def load_blueprints(self, subdir):

        bp_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), subdir
        )
        return {
            'hosts': self._load(os.path.join(bp_dir, "hosts.yaml")),
            'networks': self._load(os.path.join(bp_dir, "networks.yaml")),
            'services': self._load(os.path.join(bp_dir, "services.yaml")),
            'vars': self._load(os.path.join(bp_dir, "vars.yaml"))
        }

    def _load(self, path):

        try:
            with open(path) as fh:
                data = yaml.safe_load(fh)
        except exception as e: #(
        #         KeyError, TypeError, UnicodeDecodeError,
        #         yaml.scanner.ScannerError, yaml.parser.ParserError
        # ):
            print(e)
            raise BlueprintLoaderError(f"Not a YAML file: {path}")

        return data
