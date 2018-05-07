import sublime
import sublime_plugin

from .stack_chase_region import StackChaseRegion

# TODO: Move this to some constants file.
STACK_CHASE_TAB_TITLE = 'Stack Chase'

class StackChaseCommand(sublime_plugin.WindowCommand):
    def run(self):
        active_view = self.window.active_view()
        if STACK_CHASE_TAB_TITLE == active_view.name():
            insert_at = self.get_function_around_region(active_view, active_view.sel()[0]).end()
            symbols = self.get_symbols_under_cursor(active_view)
            self.add_block_from_symbol_definition(symbols, insert_at)
        else:
            self.add_block_to_stack_chase_view(active_view, active_view.sel()[0])

    def add_block_to_stack_chase_view(self, view, block, insert_at = None):
        region = self.get_function_around_region(view, block)
        sc_region = StackChaseRegion(filename = view.file_name(), region = region)
        stack_chase_view = self.select_stack_chase_view()
        if None == insert_at:
            insert_at = stack_chase_view.size()
        stack_chase_view.run_command("add_block_to_stack_chase", {"sc_region": sc_region.to_json(), "insert_at": insert_at})
        self.window.focus_view(stack_chase_view)
        stack_chase_view.show(insert_at)

    def add_location_to_stack_chase_view(self, location, insert_at):
        filename, a, (row, col) = location
        block, view = self.get_block_and_view_for_file_and_position(filename, row, col)
        self.add_block_to_stack_chase_view(view, block, insert_at)

    def select_stack_chase_view(self):
        for view in self.window.views():
            if STACK_CHASE_TAB_TITLE == view.name():
                return view
        return self.create_stack_chase_view()

    def create_stack_chase_view(self):
        # We set the syntax highlighting for the entire stack chase view
        # based on the syntax highlighting of the file from which we first
        # create the stack chase view.
        # We have to do this before we create the new tab, because the new
        # tab will become our active view immediately after we create it.
        current_view_syntax = self.window.active_view().settings().get('syntax')
        current_view_tab_size = self.window.active_view().settings().get('tab_size')
        new_view = self.window.new_file()
        new_view.set_name(STACK_CHASE_TAB_TITLE)
        new_view.set_scratch(True)
        new_view.settings().set('line_numbers', False)
        new_view.settings().set('syntax', current_view_syntax)
        new_view.settings().set('tab_size', current_view_tab_size)
        return new_view

    def get_function_around_region(self, view, region):
        blocks = self.get_all_function_blocks(view)
        for block in blocks:
            if block.intersects(region):
                return block;
        # Attempting to add a comment (or anything outside of a function
        # declaration) to the stack chase will throw an error.
        x, y = view.rowcol(region.begin())
        err_msg = ('Could not add focused block to {}. {}: Row {}, column {} '
                   'is not contained within a function declaration.'
                  ).format(STACK_CHASE_TAB_TITLE, view.file_name(), x + 1, y + 1)
        raise Exception(err_msg)

    def get_all_function_blocks(self, view):
        blocks = []
        for region in view.find_by_selector('entity.name.function'):
            region = view.full_line(region)
            # The entity.name.function selector only gets the function
            # declaration line, so move to the next character and get the
            # rest of that block to make sure we capture the entire function.
            function_region = view.indented_region(region.end() + 1)
            blocks.append(region.cover(function_region))
        return blocks

    def get_symbols_under_cursor(self, view):
        cursor_position = view.sel()[0]
        symbol_region = view.word(cursor_position)
        if symbol_region.empty():
            x, y = view.rowcol(cursor_position.begin())
            err_msg = ('Could not add focused block to {}. {}: Row {}, column {} '
                       'does not contain a symbol.'
                      ).format(STACK_CHASE_TAB_TITLE, view.file_name(), x + 1, y + 1)
            raise Exception(err_msg)
        symbols = [symbol_region]
        next_char_classification = view.classify(symbol_region.end())
        if sublime.CLASS_WORD_END & next_char_classification == sublime.CLASS_WORD_END:
            punctuated_word = view.expand_by_class(symbol_region, sublime.CLASS_PUNCTUATION_END)
            symbols.append(sublime.Region(symbol_region.begin(), punctuated_word.end()))

        return [view.substr(s) for s in symbols]

    def add_block_from_symbol_definition(self, symbols, insert_at):
        locations = []
        for a in [self.window.lookup_symbol_in_index(s) for s in symbols]:
            for l in a:
                locations.append(l)
        if not locations:
            err_msg = ('Could not find symbol \'{}\' in the current project.').format(symbols[0])
            raise Exception(err_msg)
        if 1 == len(locations):
            self.add_location_to_stack_chase_view(locations[0], insert_at)
        else:
            options = ['{}: {}'.format(l[1], l[2][0]) for l in locations]
            self.window.show_quick_panel(options, lambda i: self.add_location_to_stack_chase_view(locations[i], insert_at))

    # TODO: Side effect is that this file will stay open after we've added it
    # to the stack chase.
    def get_block_and_view_for_file_and_position(self, filename, row, col):
        file_view = self.window.open_file(filename)
        point = file_view.text_point(row, col)
        symbol_region = sublime.Region(point, point)
        region = self.get_function_around_region(file_view, symbol_region)

        return region, file_view
