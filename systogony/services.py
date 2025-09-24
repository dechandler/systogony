
import json
import logging

from collections import defaultdict, OrderedDict
from functools import cached_property

from .resource import Resource
from .exceptions import BlueprintLoaderError, MissingServiceError, NotReadySignal

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
            in self.var_inheritance.get('ports', {}).items()
        }

        if self.port_overrides == False:
            return { name: num for name, num in ports.items() }

        if type(self.port_overrides) == list:
            return {
                name: num for name, num
                in ports.items()
                if name in self.port_overrides
            }



    # def get_rules(self):


    #     allows = []
    #     for shorthand, allow_spec in self.vars.get('allows', {}).items():

    #         rtype, matches = self.env.get_priority_matches(
    #             shorthand, ['networks', 'services', 'hosts']
    #         )
    #         allows.append({
    #             'spec': allow_spec,
    #             'sources': matches
    #         })

    #     interface_groups = f

    #     port_groups = {}
    #     for allow in allows:
    #         ports_spec = allow['spec'].get('ports')
    #         if ports_spec is False:
    #             ports = {}
    #         elif not ports_spec:
    #             ports = {**self.ports}
    #         elif type(ports_spec) == list:
    #             ports = { k: v for k, v in self.ports if k in port_spec }
    #         elif type(ports_spec) == dict:
    #             ports = {**ports_spec}


    #         for name, num in ports.items():
    #             ports_key = set([name, num])
    #             if ports_key not in port_groups:
    #                 port_groups[ports_key] = []
    #             port_groups[ports_key].append(allow)


    #         ports_key = set(ports)
    #         if ports_key not in port_groups:
    #             port_groups[ports_key] = []
    #         port_groups[ports_key].append(allow)

    #         set(ports[port_name] for port_name in sorted(ports))


    # def resolve_to_rtype(
    #     self, shorthand, source_rtype_priorities, target_rtype
    # ):

    #         rtype, matches = self.env.get_priority_matches(
    #             shorthand, ['network', 'host']
    #         )
    #         if matches:

    #             if rtype == "network":



    #         _, matches = self.env.get_priority_matches(
    #             shorthand, ['service']
    #         )
    #         if matches:
    #             for





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

        if not parent:
            if self.name in self.env.svc_defaults:
                inherited = self.env.svc_defaults[self.name]
            else:
                inherited = {}

        elif parent in self.env.blueprint['services']:
            inherited = self.env.services[('service', parent)].vars

        elif parent in self.env.svc_defaults:
            inherited = self.env.svc_defaults[parent]

        else:
            raise MissingServiceError("")

        log.debug(f"Inheriting {parent} vars for {self.name}: {inherited}")

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
        rvars.update(self.spec)
        return {
            k: v for k, v
            in rvars.items()
            if k not in self.spec_var_ignores
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
                resolved_hosts = self.env.resolve_to_rtype(
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

class ServiceInstance(Resource):



    def __init__(self, env, service, host, inst_spec):

        log.debug(f"New ServiceInstance: {host.name}.{service.name}")
        log.debug(f"    Service FQN: {service.fqn}")
        log.debug(f"    Host FQN:    {host.fqn}")

        self.resource_type = "service_instance"
        self.shorthand_type_matches = [
            "service-instance", "service_instance", "instance",
            "svc_inst", "svc-inst","inst",
            "service", "svc"
        ]

        if not inst_spec:
            inst_spec = {}
        inst_spec['name'] = service.name
        super().__init__(env, inst_spec)

        self.service = service
        self.host = host
        overrides = { k: v for k, v in (inst_spec or {}).items() }
        self.port_overrides = overrides.get('ports', False)

        self.fqn = tuple([*host.fqn, *service.fqn])



        # Associated resources by type
        self.hosts = {self.host.fqn: self.host}  # static
        self.interfaces = {**host.interfaces}

        log.debug(overrides)



        if 'interfaces' in overrides:
            self.interfaces = self._get_spec_interfaces(
                overrides['interfaces']
            )
        elif 'interfaces' in service.spec:
            self.interfaces = self._get_spec_interfaces(
                service.spec['interfaces']
            )

        log.debug(f"Service Interfaces: {self.interfaces}")

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
        self.spec_var_ignores.extend(['mounts', 'interfaces', 'ports'])
        self.spec.update(service.vars)
        self.spec.update(overrides)
        # self.extra_vars.update(service.vars)
        # self.extra_vars.update(overrides)
        # self.extra_vars = {}  # default


        # Override service default ports
        # self.ports = { name: num for name, num in service.ports.items() }
        # if 'ports' in overrides:
        #     self.ports.update(overrides['ports'])
        #     #del overrides['ports']

        # 


        # self.extra_vars
        # self.vars = { k: v for k, v in (service.vars).items() }
        # self.vars.update(overrides)




        #log.debug(f"    Data: {json.dumps(self.serialized, indent=4)}")

    @property
    def extra_vars(self):

        extra_vars = {}
        extra_vars.update({
            'ports': self.ports,
            'interfaces': [ iface.network.network.name for iface in self.interfaces.values() ]
            #     iface.network.name
            #     for iface in self.interfaces.values()
            # ]
        })
        #extra_vars.update(self.)

        return extra_vars

    @property
    def ports(self):

        if self.port_overrides in [None, {}, []]:
            return {}
        elif self.port_overrides == False:
            return { name: num for name, num in self.service.ports.items() }
        elif type(self.port_overrides) == dict:
            return self.port_overrides
        elif type(self.port_overrides) == list:
            return {
                name: num for name, num
                in self.service.ports.items()
                if name in self.port_overrides
            }

    @property
    def networks(self):

        return {
            iface.network.network.fqn: iface.network.network
            for iface in self.interfaces.values()
        }


    @property
    def ifaces_by_net_fqn(self):
        return {
            iface.network.network.fqn: iface
            for iface in self.host.interfaces.values()
        }


    def _get_extra_serial_data(self):

        return {
            'service': str(self.service.fqn),
            'host': str(self.host.fqn),
            'interfaces': str(self.interfaces),
            'ports': self.ports
        }


    def _get_spec_interfaces(self, ifaces_spec):
        interfaces = {}
        if not ifaces_spec:
            return interfaces


        for shorthand in ifaces_spec:
            matches = self.env.walk_get_matches(
                shorthand, resource_types=['network']
            )
            for match_net in matches.values():
                if match_net.fqn not in self.ifaces_by_net_fqn:
                    continue
                iface = self.ifaces_by_net_fqn[match_net.fqn]
                interfaces[iface.fqn] = iface
        return interfaces
