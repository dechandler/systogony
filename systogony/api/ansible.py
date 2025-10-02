"""

"""
import json
import logging
import os
import socket

from collections import defaultdict
from functools import cached_property

from .api import ApiInterface

from ..environment import Environment


log = logging.getLogger('systogony')


class AnsibleApi(ApiInterface):

    @property
    def inventory(self):
        """

        Since service instances are `hosts` in this paradigm,
        alongside actual system hosts, group a system host
        with the service instances they host (`system_{hostname}`)
        and provide shared information in the group vars.

        Groups:
            "login_{hostname}" - host system and its service instances
            "svc_{svc_name}" - service instances
            "systems" - host system
            "services" - service
        Instances:
            "{hostname}"
            "inst_{svc_name}_{hostname}"

        Generate `all` group, as well as system and service groups

        """

        cache = self.get_cache('ansible_inventory')
        if cache:
            return cache

        env = Environment(self.config)
        hostvars = defaultdict(dict)
        hostvars.update({
            host.name: host.vars
            for host in env.hosts.values()
        })

        # Set local connection for localhost and local hostname
        hostvars['localhost']['ansible_connection'] = "local"
        local_hostname = socket.gethostname().split('.')[0]
        log.debug(f"Local hostname: {local_hostname}")
        if local_hostname in hostvars:
            hostvars[local_hostname]['ansible_connection'] = "local"


        # Groups defined for hosts in the blueprint
        blueprint_groups = defaultdict(list)

        # Auto-generated groups
        all_group = []
        system_login_groups = defaultdict(list)
        svc_groups = defaultdict(list)
        resource_type_groups = defaultdict(list)

        # Host and group vars
        system_group_vars = {}
        host_vars = {}

        # Process hosts
        for hostname, hvars in hostvars.items():

            log.debug(hvars)

            # Add host system to groups
            all_group.append(hostname)
            resource_type_groups['systems'].append(hostname)

            # Create login group and add host system
            system_login_group = f"login_{hostname}"
            system_login_groups[system_login_group].append(hostname)

            # Groups specified for host in blueprint
            for group in hvars.get('groups', []):
                blueprint_groups[group].append(hostname)

            # Differentiate between managed and unmanaged hosts
            supported_oses = [
                'centos', 'alma', 'fedora', 'atomic', 'debian', 'ubuntu'
            ]
            if hvars.get('os') in supported_oses or hostname == "localhost":
                blueprint_groups['managed'].append(hostname)
            else:
                blueprint_groups['unmanaged'].append(hostname)

            # System host may get unshared variables later
            host_vars[hostname] = {}

            # Save and remove service instances from hvars
            service_instances = hvars.get('service_instances', {})
            if 'service_instances' in hvars:
                del hvars['service_instances']

            # Set hostname for purposes of logging in
            # Depends on host being in ssh config
            hvars['ansible_host'] = hostname

            # Set cleaned hvars as the group vars for the shared login group
            system_group_vars[system_login_group] = hvars

            # For each service instance:
            #   - generate its associated service group
            #   - generate the inst quasi-host
            #   - add it to groups:
            #       - all
            #       - its service group
            #       - its shared login group
            for svc_name, inst in service_instances.items():
                inst['host'] = hostname

                inst_name = f"{hostname}_{svc_name}"
                svc_group = f"svc_{svc_name}"

                # Add instance to all, and its resource type
                # and service groups
                all_group.append(inst_name)
                resource_type_groups['service_instances'].append(inst_name)
                svc_groups[svc_group].append(inst_name)

                # Add inst to system login group
                system_login_groups[system_login_group].append(inst_name)

                # Set instance vars
                host_vars[inst_name] = inst

        # Set group membership
        group_hosts = {'all': all_group}
        group_hosts.update(system_login_groups)
        group_hosts.update(svc_groups)
        group_hosts.update(resource_type_groups)
        group_hosts.update(blueprint_groups)



        # Set group variables
        gvars = {'all': env.blueprint['vars'] or {}}
        gvars.update(system_group_vars)

        # Construct and return properly formatted inventory
        inventory = {
            '_meta': {
                'hostvars': host_vars
            },
            **{
                name: {
                    'hosts': hosts,
                    'vars': gvars.get(name) or {}
                }
                for name, hosts in group_hosts.items()
            }

        }

        self.write_cache(inventory, 'ansible_inventory')

        return inventory
