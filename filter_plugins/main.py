
class FilterModule:


    def filters(self):

        return {
            'group_match': self.group_match
        }


    def group_match(self, matches, group_names):

        for group in matches:
            if group in group_names:
                return True
        return False