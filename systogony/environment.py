
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

from .exceptions import (
    BlueprintLoaderError,
    NonMatchingPathSignal,
    MissingServiceError,
    NotReadySignal
)


log = logging.getLogger("systogony")


class SystogonyEnvironment:

    def __init__(self, subdir):

        self.blueprint = self.load_blueprints(subdir)
        self.svc_defaults = self.load_service_defaults()

        log.debug(self.svc_defaults)

        # Index of resources by base name
        self.names = defaultdict(list)

        (
            self.hosts, self.host_groups,
            self.networks, self.interfaces,
            self.services, self.service_instances,
            self.acls
        ) = {}, {}, {}, {}, {}, {}, {}


        #self.resources = {}
        self.hosts, self.host_groups = self._get_hosts()
        self.networks = self._get_networks()
        self._populate_interfaces()
        self.services = self._get_services()
        self._populate_service_instances()

        self.acls = {}




        # for iface in host.interfaces.values():






        # Load service defaults



        # for service in self.services.values():
        #     service.get_rules()


        # Resolve shorthands in service allow/access
        # for service in self.services.values():
        #     service.apply_rules()


        # # Generate acls
        for resource in self.resources.values():
            resource.gen_acls()


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
            f"net_{network.short_fqn_str}": network.vars
            for network in self.networks.values()
            if network.net_type != "isolated"
        })
        env_hostvars.update({
            f"svc_{service.short_fqn_str}": {}  # service.vars
            for service in self.services.values()
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
            meta_name = f"net_{network.short_fqn_str}"
            if meta_name in groups['network_metahosts']:
                continue
            groups["network_metahosts"].append(meta_name)
            groups[meta_name] = [
                host.name for host in network.hosts.values()
            ]

        for service in self.services.values():
            meta_name = f"svc_{service.short_fqn_str}"
            if meta_name in groups["service_metahosts"]:
                continue
            groups["service_metahosts"].append(meta_name)
            groups[meta_name] = [
                inst.host.name for inst in service.service_instances.values()
            ]

        return groups

    def _get_hosts(self):

        hosts = {}
        host_groups = defaultdict(list)

        for host_name, host_spec in self.blueprint['hosts'].items():
            host_spec = {} if host_spec is None else host_spec
            host_spec['name'] = host_name
            host = Host(self, host_spec)
            fqn = tuple(host.fqn)

            hosts[fqn] = host
            for group_name in host.groups:
                host_groups[group_name].append(host)

        for group_name, host_list in self.host_groups.items():
            host_groups[group_name] = sorted(host_list)

        return hosts, host_groups


    def _get_networks(self):

        networks = {}

        # Generate WAN pseudo-network
        networks[(('network', 'wan'),)] = Network(
            self, {'name': "wan", 'type': "wan", 'cidr': "0.0.0.0/0"}
        )

        # Create top level network objects
        for net_name, net_spec in self.blueprint['networks'].items():
            net_spec['name'] = net_name
            net = Network(self, net_spec)
            networks[net.fqn] = net

            for subnet in net.get_descendents(types=['networks']):
                networks[subnet.fqn] = subnet

        return networks

    def _populate_interfaces(self):
        # Generate interfaces to connect host to network
        for host in self.hosts.values():
            host.add_interfaces()

    def _get_services(self):
        services = {}
        for svc_name, svc_bp in self.blueprint['services'].items():
            svc_bp['name'] = svc_name
            services[('service', svc_name)] = Service(self, svc_bp)
        return services

    def _populate_service_instances(self):
        # Populate services
        prev_populated_services_len = -1
        populated_services = []
        while (
            len(populated_services) < len(self.services)
            and len(populated_services) != prev_populated_services_len
        ):
            prev_populated_services_len = len(populated_services)
            for svc in self.services.values():
                if svc.hosts_complete:
                    continue
                try:
                    svc.populate_hosts()
                except NotReadySignal:
                    continue
                populated_services.append(svc.name)

    def _get_group_for_network(self, network):

        name = f"net_{network.name}"
        hosts = []
        gvars = {'cidr': network.cidr}
        if network.rules['forward']:
            gvars['rules'] = network.rules

        return name, hosts, gvars


    def gen_acl(self, origin, acl_spec, sources, destinations):
        """


        Called from Resource._gen_acls_by_spec_type
        """
        Acl(self, origin, acl_spec, sources, destinations)


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



    def load_service_defaults(self):

        raw_defaults = {}
        defaults = {}
        resolved = []

        defaults_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "services.d"
        )
        log.debug(f"Svc defaults directory: {defaults_dir}")
        for root, dirs, files in os.walk(defaults_dir):
            for f in files:
                svc_name, extension = os.path.splitext(f)
                if extension != ".yaml":
                    continue
                path = os.path.join(root, f)
                try:
                    svc_vars = self._load(path)
                except BlueprintLoaderError:
                    log.warning(f"yaml file in services.d not parsing: {path}")
                    continue
                if svc_vars.get('service') in [svc_name, None]:
                    svc_vars['service'] = svc_name
                    defaults[svc_name] = svc_vars
                    resolved.append(svc_name)
                raw_defaults[svc_name] = svc_vars

        log.debug(f"Resolved service defaults: {resolved}")
        # Resolve services iteratively until complete or unchanged
        prev_resolved_len = -1
        while (
            len(resolved) < len(raw_defaults)
            and len(resolved) != prev_resolved_len
        ):
            prev_resolved_len = len(defaults)

            for svc_name, svc_vars in defaults.items():
                if svc_name in defaults:
                    continue

                # Load defaults from parent service
                parent_svc_name = svc_vars['service']
                try:
                    parent_vars = {**defaults[parent_svc_name]}
                except KeyError:
                    raise MissingServiceError(f"Missing from service.d: {parent_service} ({svc_name}.yaml)")

                # Update service vars with parent defaults
                del svc_vars['service']
                parent_vars.update(svc_vars)
                defaults[svc_name] = parent_vars

                # Mark complete if resolved
                if parent_vars['service'] == parent_svc_name:
                    resolved.append(parent_svc_name)

        if len(resolved) < len(raw_defaults):
            log.warn(f"Unresolved services: {set(defaults) - set(resolved)}")

        return defaults


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
        except Exception as e: #(
        #         KeyError, TypeError, UnicodeDecodeError,
        #         yaml.scanner.ScannerError, yaml.parser.ParserError
        # ):
            print(e)
            raise BlueprintLoaderError(f"Not a YAML file: {path}")

        return data
