import sublime, sublime_plugin, os, re, fnmatch, subprocess, time

class FindRailsFiles():
  def set_project_folder(self):
    self.project_folder = None if len(self.window.folders()) == 0 else self.window.folders()[0]
    return self.project_folder

  def partner_filepath(self, filepath):
    is_test_file = re.match(r"^(.+?)_test\.rb", filepath)

    if is_test_file:  # is test file, so get code file
      filepath = is_test_file.group(1) + '.rb'
      filepath = self.recursive_find('app', filepath)
      method_name = self.method_name_from_text(True, test_method=True)

    else:             # is code file, add test suffix and get test file
      filepath = filepath.replace('.rb', '') + '_test.rb'
      filepath = self.recursive_find('test', filepath)
      method_name = self.method_name_from_text(True, test_method=False)

    return is_test_file, filepath, method_name

  # checking to see if we're in a subfolder 2-deep or more.
  def subfolder_paths(self, filepath):
    relative_path = os.path.split(filepath)[0].replace(self.project_folder, '')
    paths = relative_path.split('/')[3:]
    return None if len(paths) == 0 else '/' + '/'.join(paths)

  def recursive_find(self, relative_folder, filepath):
    base_folder = os.path.join(self.project_folder, relative_folder)
    filename = os.path.basename(filepath)
    subfolders = self.subfolder_paths(filepath)
    finds = self.recursive_glob(base_folder, filename,subfolders)
    return None if len(finds) == 0 else finds[0]

  def recursive_glob(self, base_folder, pattern, required_dir = None):
    results = []
    for base, dirs, files in os.walk(base_folder):
      if (required_dir is None) or (required_dir in base):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
      if len(dirs) > 0:
        for dir in dirs:
          results = results + self.recursive_glob(os.path.join(base, dir), pattern, required_dir)
    return results

  # TODO: make this pass in a prefix instead of test_method toggle
  def method_name_from_text(self, reverse_lookup = True, test_method = False):
    method_name = None
    view = self.view
    cursor_location = view.sel()[0].a
    if reverse_lookup:
      region = sublime.Region(0, cursor_location)
    else:
      region = sublime.Region(cursor_location, view.size())
    text_up_to_cursor = view.substr(region)
    lines = text_up_to_cursor.split("\n")
    if reverse_lookup:
      lines.reverse()
    for line in lines:
      if test_method:
        method_name_match = re.match(r"^.*?def\s+(test_.+?)(\?\(|$|\s)", line)
      else:
        method_name_match = re.match(r"^.*?def\s+(.+?)(\?\(|$|\s)", line)

      if method_name_match:
        method_name = method_name_match.group(1)
        break
    return method_name


class RailsTestRunner:
  def run_tests(self, test_name = None):
    if not self.set_project_folder():
      return

    self.view = self.window.active_view()
    filepath = self.view.file_name()
    if os.path.splitext(filepath)[1] != '.rb':
      return

    is_test_file, test_filepath, method_name = self.partner_filepath(filepath)
    if is_test_file:
      test_filepath = filepath
    else:
      if not test_filepath: # couldn't find a matching test file
        return

    self.window.open_file(test_filepath)

    settings = sublime.load_settings('RailsTest.sublime-settings')
    osascript = settings.get("osascript") or "/usr/bin/osascript"
    applescript_path = "{packages_dir}/RailsTest/rails_test.{terminal_name}.applescript".format(
      packages_dir = sublime.packages_path(),
      terminal_name = settings.get("terminal")
    )
    project_settings = self.ensure_project_settings_has_rails_test_settings()

    apple_commands = [
      osascript,
      applescript_path,
      project_settings['rvm_initialization'],
      self.project_folder,
      re.sub(self.project_folder + '/', '', test_filepath)
    ]

    if test_name:
      apple_commands.append(test_name)

    subprocess.Popen(apple_commands)


  def ensure_project_settings_has_rails_test_settings(self):
    settings = self.window.project_data()
    if self.project_settings_key in settings:
      # ensure that all keys have a default, in case something got deleted, by merging with the default settings.
      # any existing settings will win.
      full_settings = dict( list(self.default_settings.items()) + list(settings[self.project_settings_key].items()) )

      # save back to project settings if there are changes
      if settings[self.project_settings_key] != full_settings:
        sublime.status_message("Updated project settings.")
        self.window.set_project_data(settings)
    else:
      # not set up yet, so add the autocomplete settings node to the project settings
      settings[self.project_settings_key] = self.default_settings
      self.window.set_project_data(settings)

    return settings[self.project_settings_key]


  @property
  def project_settings_key(self):
    return 'rails_test_settings'

  @property
  def base_path(self):
    return os.path.join(sublime.packages_path(), 'RailsTest')

  @property
  def default_settings(self):
    return {
      'rvm_initialization': '[[ -s "$HOME/.rvm/scripts/rvm" ]] && source "$HOME/.rvm/scripts/rvm"; rvm 1.9.3; ruby -v',
    }


class RailsTestWithNameCommand(RailsTestRunner, FindRailsFiles, sublime_plugin.WindowCommand):
  def run(self):
    # get test name just before cursor
    self.view = self.window.active_view()
    test_name = self.method_name_from_text(True, test_method=True)
    if not test_name:
      # otherwise cursor is above first test, so get the first test name after
      test_name = self.method_name_from_text(False, test_method=True)
    self.run_tests(test_name)


# utility commands for this plugin
class OpenProjectFileCommand(sublime_plugin.WindowCommand):
    def run(self):
      project_file = self.window.project_file_name()
      if project_file:
        self.window.open_file(project_file)


class RailsTestCommand(RailsTestRunner, FindRailsFiles, sublime_plugin.WindowCommand):
  def run(self):
    self.run_tests()


class LoadListener(sublime_plugin.EventListener):
  def on_load_async(self, view):
    action = ToggleRailsTestFileCommand.current_open_action
    if not action:
      return
    if view == action.view:
      CursorMover().move_cursor_to_method(action)
      ToggleRailsTestFileCommand.current_open_action = None

class OnLoadViewAction():
  def __init__(self, view, method_name, is_test_file):
    self.view, self.method_name, self.is_test_file = view, method_name, is_test_file

class CursorMover(FindRailsFiles):
  def move_cursor_to_method(self, action):
    view, method_name, is_test_file = action.view, action.method_name, action.is_test_file
    self.view = view

    # find the matching method location in partner file
    if is_test_file:
      method_name = method_name.replace('test_', '')
    else:
      method_name = 'test_' + method_name
    line = view.find('def\s+%s' % method_name, 0)
    if line.a == -1:  # couldn't find matching method
      return

    print(method_name, line.a)
    line = view.line(line) # full line

    # if cursor is not in method, then move cursor to that method
    current_method_name = self.method_name_from_text()
    if current_method_name != method_name:
      view.sel().clear()
      view.sel().add(sublime.Region(line.b + 1))

    # scroll to method
    view.show(line)

class ToggleRailsTestFileCommand(FindRailsFiles, sublime_plugin.WindowCommand):
  current_open_action = None

  def run(self):
    if not self.set_project_folder():
      return

    self.view = self.window.active_view()
    filepath = self.view.file_name()
    is_test_file, filepath, method_name = self.partner_filepath(filepath)
    if filepath is None:
      return

    was_open = self.window.find_open_file(filepath)
    view = self.window.open_file(filepath)
    if method_name is not None:
      # if file was not open, try to move to the selected method
      action = OnLoadViewAction(view, method_name, is_test_file)
      if not was_open:
        ToggleRailsTestFileCommand.current_open_action = action
      else:
        CursorMover().move_cursor_to_method(action)
