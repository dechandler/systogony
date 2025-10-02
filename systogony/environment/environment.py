
import json
import logging
import os

from collections import defaultdict
from functools import cached_property

import yaml

from .query import ResourceShorthandQuery
from .blueprint import Blueprint

from ..resource import Acl, Host, Interface, Network, Service, ServiceInstance

from ..exceptions import (
    BlueprintLoaderError,
    NonMatchingPathSignal,
    MissingServiceError,
    NotReadySignal
)


log = logging.getLogger("systogony")


class Environment:

    def __init__(self, config):

        self.config = config

        self.query = ResourceShorthandQuery(config, self)

        self.blueprint = Blueprint(config)

        self.svc_defaults = config['service_defaults']

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


        # # Generate acls
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
