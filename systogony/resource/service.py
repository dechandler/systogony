
import json
import logging

from collections import defaultdict, OrderedDict
from functools import cached_property

from .resource import Resource
from .service_instance import ServiceInstance

from ..exceptions import BlueprintLoaderError, MissingServiceError, NotReadySignal

log = logging.getLogger("systogony")


class Service(Resource):



    def __init__(self, env, svc_spec):

        log.info(f"New Service: {svc_spec['name']}")
        log.debug(f"    Spec: {json.dumps(svc_spec)}")

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


        # Other attributes
        self.port_overrides = self.spec.get('ports', False)
        #self.ports = self.spec.get('ports', {})

        #self.spec_var_ignores.extend(['ports'])
        # self.extra_vars = {}  # default


        self.parents = []

        log.debug(f"Service data: {json.dumps(self.serialized, indent=4)}")

    @property
    def ports(self):

        if self.port_overrides in [None, {}, []]:
            return {}
        if type(self.port_overrides) == dict:
            return self.port_overrides

        ports = {
            name: num for name, num
            in (self.var_inheritance.get('ports') or {}).items()
        }

        if self.port_overrides == False:
            return { name: num for name, num in ports.items() }

        if type(self.port_overrides) == list:
            return {
                name: num for name, num
                in ports.items()
                if name in self.port_overrides
            }



    @property
    def hosts(self):

        return {
            inst.host.fqn: inst.host
            for inst in self.service_instances.values()
        }

    @property
    def networks(self):

        return {
            iface.network.network.fqn: iface.network.network
            for iface in self.interfaces.values()
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

    @property
    def var_inheritance(self):

        parent = self.spec.get('service')
        log.debug(f"{self.name} inherits from {parent}")

        if not parent:
            self.spec['service'] = self.name
            if self.name in self.env.svc_defaults:
                inherited = self.env.svc_defaults[self.name]
            else:
                inherited = {}

        elif parent in self.env.svc_defaults:
            self.spec['service'] = parent
            inherited = self.env.svc_defaults[parent]

        elif parent in self.env.blueprint['services']:
            if parent == self.name:
                inherited = {}
            else:
                inherited = self.env.services[('service', parent)].vars
        else:
            raise MissingServiceError("")

        log.debug(f"{self.name} inherits from {parent}: {inherited}")

        return {
            k: v for k, v
            in inherited.items()
        }

    @property
    def vars(self):

        log.debug("SERVICE VARS")
        rvars = {
            k: v for k, v
            in self.var_inheritance.items()
        }
        log.debug(f"  Inheriting: {rvars}")
        rvars.update(self.spec)

        return {
            k: v for k, v in rvars.items()
            if k not in self.spec_var_ignores
        }



    def handle_access(self):

        for shorthand, overrides in self.spec.get('access', {}).items():

            resolved_hosts = self.env.query.resolve_to_rtype(
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
            f"Attempting to populate hosts for {self.name}:",
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
                resolved_hosts = self.env.query.resolve_to_rtype(
                    shorthand,
                    ['host', 'service_instance', 'service', 'network'],
                    'hosts'
                )
            except BlueprintLoaderError:
                log.error(f"BlueprintLoaderError for {self.name}: {shorthand}")
                raise BlueprintLoaderError(f'Shorthand "{shorthand}" under service hosts {self.name}')

            if not resolved_hosts:
                log.debug(f"Failed to resolve hosts for {self.name}: {shorthand}")
                raise NotReadySignal(f"No hosts for {shorthand}")

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

