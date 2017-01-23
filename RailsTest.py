import sublime, sublime_plugin, os, re, fnmatch, subprocess, time, glob

class FindRailsFiles():
  def set_project_folder(self):
    self.project_folder = None if len(self.window.folders()) == 0 else self.window.folders()[0]
    return self.project_folder

  def partner_filepath(self, filepath):
    filedir, filename = os.path.split(filepath)
    is_test_file = re.match(r"^(.+?)_test\.rb", filename)
    is_subtest_file = re.match(r"^(.+?)_tests\.rb", filename)

    # is test file (ends with 'test'), so get code file
    # subtest file - ends with 'tests' and belongs to the parent folder
    if is_test_file or is_subtest_file:
      if is_test_file:
        filename = is_test_file.group(1) + '.rb'
      else:
        filename = filedir.split('/')[-1] + '.rb'
        is_test_file = is_subtest_file

      filepath = self.recursive_find(filedir, filename, ['app', 'lib'])
      method_name = self.method_name_from_cursor_location_in_code(True, test_method=True)

    else:             # is code file, add test suffix and get test file
      filename = filename.replace('.rb', '') + '_test.rb'
      filepath = self.recursive_find(filedir, filename, ['test'])
      method_name = self.method_name_from_cursor_location_in_code(True, test_method=False)

    return is_test_file, filepath, method_name

  def recursive_find(self, filedir, filename, target_folders):
    finds = []
    for target_folder in target_folders:
      # base_folder = os.path.join(self.project_folder, target_folder)
      # base_folder = self.project_folder

      prefix, namespace = self.subfolder_paths(filedir)
      if prefix == '':
        base_folder = os.path.join(self.project_folder, target_folder)
      else:
        # dang python is too stupid to realize that prefix is not an absolute path, gotta make adjustments
        prefix = re.match(r"(\/)*(.+?)$", prefix).group(2)
        base_folder = os.path.join(self.project_folder, prefix, target_folder)

      finds += self.rglob(base_folder, filename)

    # now try to find the namespaced version, if required
    if namespace != '':
      namespace_matches =  [path for path in finds if namespace in path]
      if len(namespace_matches) > 0:
        finds = namespace_matches

    return None if len(finds) == 0 else finds[0]

  # checking to see if we're in a subfolder 2-deep or more.
  def subfolder_paths(self, filedir):
    relative_path = filedir.replace(self.project_folder, '')
    regex = re.compile(r"""
      (.*?)
      \/(test/unit|
         test/functional|
         test/integration|
         app/concerns|
         app/controllers|
         app/decorators|
         app/helpers|
         app/mailers|
         app/models|
         app/services|
         lib)(.*?)$
    """, re.VERBOSE)
    match = regex.match(relative_path)
    if match:
      return [match.group(1), match.group(3)]
    else:
      return ['', '']

  # where to look for matching code or test files
  @property
  def valid_dirs(self):
    return ['app', 'test', 'lib', 'vendor']

  # will ignore these if found inside above valid_dirs
  def is_invalid_dir(self, dirname):
    return re.match(r".*(tmp|script|views|fixtures|helpers|assets|bundle|\.git|db|config)", dirname)

  # from http://cpiekarski.com/2011/09/23/python-recursive-glob/
  def rglob(self, base, pattern):
    flist = []
    # first get files in the dir
    flist.extend(glob.glob(os.path.join(base, pattern)))

    # now recursively search in this dir's dirs
    # dirs = [path for path in glob.iglob(os.path.join( base, '*')) if os.path.isdir(path) and not self.is_invalid_dir(path) ]
    dirs = []
    for dir in [x[1] for x in os.walk(base)][0]:
      if not self.is_invalid_dir(dir):
        dirs.append(dir)

    if len(dirs):
      for dir in dirs:
        flist.extend(self.rglob(os.path.join(base, dir), pattern))
    return flist

  # TODO: make this pass in a prefix instead of test_method toggle
  def method_name_from_cursor_location_in_code(self, reverse_lookup = True, test_method = False):
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

    is_test_file, partner_filepath, method_name = self.partner_filepath(filepath)
    if is_test_file:
      # make adjustments to the current test file path for tests in self-named subfolder
      filedir, filename = os.path.split(filepath)
      is_subtest_file = re.match(r"^(.+?)_tests\.rb", filename)
      if is_subtest_file:
        # e.g. test/unit/company/roles_tests.rb => test/unit/company_test.rb
        test_filepath = filedir + '_test.rb'
      else:
        # test/unit/company_test.rb, so just use as is
        test_filepath = filepath
    else:
      if not test_filepath: # couldn't find a matching test file
        return

    if filepath != test_filepath and not is_subtest_file:
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
    # add toggle to let applescript at the ONLY=type prefix
    if is_subtest_file and not test_name:
      apple_commands.append('none')
      apple_commands.append(is_subtest_file.group(1))

    print(apple_commands)
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
    test_name = self.method_name_from_cursor_location_in_code(True, test_method=True)
    if not test_name:
      # otherwise cursor is above first test, so get the first test name after
      test_name = self.method_name_from_cursor_location_in_code(False, test_method=True)
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

    line = view.line(line) # full line

    # if cursor is not in method, then move cursor to that method
    current_method_name = self.method_name_from_cursor_location_in_code()
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
