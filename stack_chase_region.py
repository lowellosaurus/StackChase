import json
import sublime

class StackChaseRegion(object):
    def __init__(self, filename, region):
        self.filename = filename
        self.home_region = region

    def get_key(self):
        return '{}:{}'.format(self.filename, self.get_first_line_num())

    # TODO: What is the idiomatic way to serialize python objects?
    def to_json(self):
        return json.dumps({
            'filename': self.filename,
            'home_region': [self.home_region.begin(), self.home_region.end()],
            })

    def from_json(json_str):
        anon_obj = json.loads(json_str)

        filename = anon_obj['filename']
        region = sublime.Region(anon_obj['home_region'][0], anon_obj['home_region'][1])

        return StackChaseRegion(filename = filename, region = region)

    def get_home_file_view(self):
        window = sublime.active_window()
        home_file = window.find_open_file(self.filename)
        
        # TODO: Handle this case later.
        if None == home_file:
            raise Exception("We should open a new file, read from that file, and close it if that file is not already open")

        return home_file

    def get_text(self):
        return self.get_home_file_view().substr(self.home_region)

    def get_first_line_num(self):
        return self.get_home_file_view().rowcol(self.home_region.begin())[0]