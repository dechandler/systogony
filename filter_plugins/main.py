
class FilterModule:


    def filters(self):

        return {
            'group_match': self.group_match,
            'dict_update': self.dict_update
        }


    def group_match(self, matches, group_names):

        for group in matches:
            if group in group_names:
                return True
        return False


    def dict_update(self, original, updates):

        original.update(updates)
        return original
