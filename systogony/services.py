
import json
import logging

from collections import defaultdict, OrderedDict
from functools import cached_property

from .resource import Resource
from .exceptions import BlueprintLoaderError

log = logging.getLogger("systogony")


class Service(Resource):



    def __init__(self, env, svc_spec):

        log.debug(f"New Service - spec: {json.dumps(svc_spec)}")

        self.resource_type = "service"
        self.shorthand_type_matches = ["service", "svc"]

        super().__init__(env, svc_spec)

        self.hosts_complete = False


        # Associated resources by type
        # self.networks = 
        self.services = {self.fqn: self}  # static (self)
        self.service_instances = {}  # registry of ServiceInstance by fqn

        # Lineage for walking up and down the heirarchy
        self.parent = None
        self.children = self.service_instances


        self.allows = {}

        # Other attributes
        self.ports = self.spec.get('ports', {})

        self.spec_var_ignores.extend(['ports'])
        # self.extra_vars = {}  # default


        self.parents = []

        log.debug(f"Service data: {json.dumps(self.serialized, indent=4)}")

    @property
    def hosts(self):

        return {
            inst.host.fqn: inst.host
            for inst in self.service_instances.values()
        }

    @property
    def interfaces(self):

        ifaces = {}
        for inst in self.service_instances.values():
            ifaces.update(inst.interfaces)
        return ifaces


    def _get_extra_serial_data(self):

        return {
            'service_instances': [
                str(fqn)
                for fqn in self.service_instances
                #for inst in inst_list
            ]


            #self._fqn_str_list(self.service_instances),
            #'allows': self.allows
        }



    def handle_access(self):

        for shorthand, overrides in self.spec.get('access', {}).items():

            resolved_hosts = self.env.resolve_to_rtype(
                shorthand,
                ['service', 'service_instance', 'host', 'network', 'interface'],
                'hosts'
            )
            for host in resolved_hosts.values():
                for inst in self.service_instances.values():
                    host.allows[inst.host.fqn] = {
                        'host': inst.host, 'overrides': overrides
                    }


    def populate_hosts(self):

        log.debug(' '.join([
            "Attempting to populate hosts:",
            '.'.join([ '.'.join(pair) for pair in self.fqn ])
        ]))

        # All shorthands have resolved previously, so skip
        if self.hosts_complete:
            return

        # Generate list of hosts but return if any shorthands have no matches
        hosts = {}
        host_identifiers = {}
        for shorthand in self.spec.get('hosts', {}):
            try:
                resolved_hosts = self.env.resolve_to_rtype(
                    shorthand,
                    ['host', 'service_instance', 'service', 'network'],
                    'hosts'
                )
                assert resolved_hosts
            except (BlueprintLoaderError, AssertionError):
                return {}

            hosts.update(resolved_hosts)
            host_identifiers.update({
                host.fqn: shorthand
                for host in resolved_hosts.values()
            })
            host_identifiers[shorthand] = resolved_hosts

        # Mark all host shorthands resolved
        self.hosts_complete = True

        # Generate service instances on matching hosts
        instance_names = []
        for host in hosts.values():
            shorthand = host_identifiers[host.fqn]
            overrides = self.spec.get('hosts', {}).get(shorthand)
            inst = ServiceInstance(self.env, self, host, overrides)
            instance_names.append(inst.host.name)

        log.info(' '.join([
            f"Hosts running {self.name}:",
            ', '.join(instance_names)
        ]))

class ServiceInstance(Resource):



    def __init__(self, env, service, host, overrides):

        log.debug(f"New ServiceInstance: {host.name}.{service.name}")
        log.debug(f"    Service FQN: {service.fqn}")
        log.debug(f"    Host FQN:    {host.fqn}")

        self.resource_type = "service_instance"
        self.shorthand_type_matches = [
            "service-instance", "service_instance", "instance",
            "svc_inst", "svc-inst","inst",
            "service", "svc"
        ]

        super().__init__(env, {'name': service.name})

        self.service = service
        self.host = host
        overrides = { k: v for k, v in (overrides or {}).items() }

        self.fqn = tuple([*host.fqn, *service.fqn])



        # Associated resources by type
        self.hosts = {self.host.fqn: self.host}  # static
        self.interfaces = {
            fqn: interface for fqn, interface in host.interfaces.items()
        }
        if 'interfaces' in overrides:
            interfaces = {}
            for shorthand in overrides:
                matches = self.env.walk_get_matches(
                    shorthand, resource_types=['interface']
                )
                interfaces.update({
                    match_iface.fqn: self.interfaces[match_iface.fqn]
                    for match_iface in matches.items()
                    if match_interface.fqn in self.interfaces
                })
            self.interfaces = interfaces
            del overrides['interfaces']

        #self.networks = 
        self.services = {self.service.fqn: self.service}  # static
        self.service_instances = {self.fqn: self}  # static (self)


        # Register this resource
        service.service_instances[host.fqn] = self
        host.service_instances[service.fqn] = self
        for iface in self.interfaces.values():
            iface.service_instances[self.fqn] = self


        # Lineage for walking up and down the heirarchy
        self.parents = [*self.interfaces.values(), host]
        #self.parent = 


        # Other attributes
        self.spec_var_ignores.extend(['mounts'])
        self.spec.update(service.vars)
        self.spec.update(overrides)
        # self.extra_vars.update(service.vars)
        # self.extra_vars.update(overrides)
        # self.extra_vars = {}  # default


        # Override service default ports
        self.ports = { name: num for name, num in service.ports.items() }
        if 'ports' in overrides:
            self.ports.update(overrides['ports'])
            del overrides['ports']

        # 


        # self.extra_vars
        # self.vars = { k: v for k, v in (service.vars).items() }
        # self.vars.update(overrides)




        log.debug(f"    Data: {json.dumps(self.serialized, indent=4)}")

    @cached_property
    def extra_vars(self):

        extra_vars = {}
        extra_vars['ports'] = self.ports
        #extra_vars.update(self.)

        return extra_vars


    def _get_extra_serial_data(self):

        return {
            'service': str(self.service.fqn),
            'host': str(self.host.fqn),
            'interfaces': str(self.interfaces),
            'ports': self.ports
        }
