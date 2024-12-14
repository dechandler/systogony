
class FilterModule:


    def filters(self):

        return {
            'group_match': self.group_match,
            'has_service': self.has_service,
            'dict_update': self.dict_update,
            'deep_get': self.deep_get
        }


    def group_match(self, matches, group_names):

        for group in matches:
            if group in group_names:
                return True
        return False


    def has_service(self, hostname, service, svc_map):

        if hostname in self.deep_get(svc_map, [service, 'hosts']):
            return True


    def dict_update(self, original, updates):

        original.update(updates)
        return original


    def deep_get(self, this_dict, dict_path, default=None):

        if not dict_path:
            return this_dict

        if type(dict_path) == str:
            dict_path = dict_path.split('.')

        key = dict_path.pop(0)
        try:
            return self.deep_get(this_dict[key], dict_path, default)
        except KeyError:
            return default