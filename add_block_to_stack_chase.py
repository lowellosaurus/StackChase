import re
import sublime
import sublime_plugin

from .stack_chase_region import StackChaseRegion

STACK_CHASE_TAB_TITLE = 'Stack Chase'

# TODO: Can we use the colors defined in the current theme?
HEADLINE_TEXT_STYLE = """
    <style>
        span { color: color(var(--background) blend(var(--purplish) 50%); }
    </style>
"""

# white-space: pre; is not supported. As such we resort to using 0 padding.
GUTTER_TEXT_STYLE = """
    <style>
        span { color: color(var(--background) blend(var(--foreground) 75%); }
        span.no-show { color: rgba(0,0,0, 0); }
    </style>
"""

# https://stackoverflow.com/questions/20182008/sublime-text-3-api-get-all-text-from-a-file


class AddBlockToStackChaseCommand(sublime_plugin.TextCommand):
    # TODO: We should be adding the region we want to add to an array of
    # regions in the stack chase, not directly pasting strings.
    # Perhaps we can use Settings and PhantomSet.
    def run(self, edit, sc_region, insert_at=None):
        sc_region = StackChaseRegion.from_json(sc_region)
        self.add_to_sc_region_dict(sc_region)
        inserted_char_cnt = self.view.insert(
            edit, insert_at, sc_region.get_text())
        sc_region.foreign_region = sublime.Region(
            insert_at, insert_at + inserted_char_cnt)
        self.format_region(edit, sc_region)

    def add_to_sc_region_dict(self, sc_region):
        if not self.view.settings().has(STACK_CHASE_TAB_TITLE):
            self.view.settings().set(STACK_CHASE_TAB_TITLE, {})
        regions = self.view.settings().get(STACK_CHASE_TAB_TITLE)
        regions[sc_region.get_key()] = sc_region.to_json()
        self.view.settings().set(STACK_CHASE_TAB_TITLE, regions)

    def format_region(self, edit, sc_region):
        key = sc_region.get_key()
        og_region = sc_region.foreign_region
        first_line_num = sc_region.get_first_line_num()
        # Add a newline before the start of the text in this region so we can
        # add the filename before the block.
        inserted_char_cnt = self.view.insert(edit, og_region.begin(), "\n")
        line_key = key + 'before'
        content = HEADLINE_TEXT_STYLE + '<span>' + sc_region.filename + '</span>'
        self.view.add_phantom(line_key, og_region,
                              content, sublime.LAYOUT_INLINE)
        # Offset the region by the number of characters we added in the step above.
        region = sublime.Region(
            og_region.begin() + inserted_char_cnt, og_region.end() + inserted_char_cnt)
        line_num_fmt = self.get_line_number_format()
        for i, line in enumerate(self.view.split_by_newlines(region)):
            line_key = key + str(i)

            line_num = first_line_num + i
            padded_num = line_num_fmt.format(line_num)
            components = re.findall('^(0*)(.*)$', padded_num)[0]
            content = GUTTER_TEXT_STYLE + '<span>' + '<span class="no-show">' + \
                components[0] + '</span>' + components[1] + '</span>'

            self.view.add_phantom(line_key, line, content,
                                  sublime.LAYOUT_INLINE)
        # Add one line of space after the last line of the block.
        line_key = key + 'after'
        content = '<br>'
        after_region = sublime.Region(og_region.end(), og_region.end())
        self.view.add_phantom(line_key, after_region,
                              content, sublime.LAYOUT_BLOCK)

    # tab_size setting set when we first created the stack chase view.
    # Left pad in increments of the number of spaces for each tab.
    def get_line_number_format(self):
        left_pad_length, minimum_left_pad_length = (0, 5)
        tab_size = self.view.settings().get('tab_size')
        while left_pad_length < minimum_left_pad_length:
            left_pad_length += tab_size

        return '{0:0' + str(left_pad_length - 1) + 'd}'
