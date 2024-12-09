
class FilterModule:


    def filters(self):

        return {
            'system_match': self.system_match
        }


    def system_match(self, matches, group_names):

        for system in matches:
            if system in group_names:
                return True
        return False