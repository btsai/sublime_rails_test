import sublime, sublime_plugin, os, re, fnmatch, subprocess

class FindRailsFiles():
  def set_project_folder(self):
    self.project_folder = None if len(self.window.folders()) == 0 else self.window.folders()[0]
    return self.project_folder

  def check_if_test_file(self, filename):
    testfile_check = re.match(r"^(.+?)_test\.rb", filename)
    code_file = testfile_check.group(1) + '.rb' if testfile_check else None
    return testfile_check, code_file

  def open_code_file(self, code_file):
    filepath = self.get_code_filepath(code_file)
    if filepath:
      self.window.open_file(filepath)

  def open_test_file(self, test_file):
    filepath = self.get_test_filepath(test_file)
    if filepath:
      self.window.open_file(filepath)

  def get_code_filepath(self, code_file):
    filepath = self.model_path(code_file) or self.controller_path(code_file)
    return filepath

  def get_test_filepath(self, test_file):
    filepath = self.unit_test_path(test_file) or self.functional_test_path(test_file)
    return filepath

  def model_path(self, filename):
    models = self.recursive_find('app/models', filename)
    if models:
      return models
    return self.recursive_find('app/services', filename)

  def controller_path(self, filename):
    return self.recursive_find('app/controllers', filename)

  def unit_test_path(self, filename):
    return self.recursive_find('test/unit', filename)

  def functional_test_path(self, filename):
    return self.recursive_find('test/functional', filename)

  def recursive_find(self, relative_folder, filename):
    base_folder = os.path.join(self.project_folder, relative_folder)
    finds = self.recursive_glob(base_folder, filename)
    if len(finds) == 0:
      return None
    else:
      return finds[0]

  # from http://stackoverflow.com/questions/2186525/use-a-glob-to-find-files-recursively-in-python
  def recursive_glob(self, base_folder, pattern):
    results = []
    for base, dirs, files in os.walk(base_folder):
      goodfiles = fnmatch.filter(files, pattern)
      results.extend(os.path.join(base, f) for f in goodfiles)
    return results


class RailsTestRunner:
  def run_tests(self, test_name = None):
    if not self.set_project_folder():
      return

    filepath = self.window.active_view().file_name()
    filename = os.path.basename(filepath)
    if os.path.splitext(filename)[1] != '.rb':
      # ignore non-rb files
      return
    is_test_file, code_file = self.check_if_test_file(filename)
    if is_test_file:
      test_filepath = filepath
    else:
      test_file = filename.replace('.rb', '') + '_test.rb'
      test_filepath = self.get_test_filepath(test_file)
      if not test_filepath:
        # couldn't find a matching test file
        return

    settings = sublime.load_settings('RailsTest.sublime-settings')
    osascript = settings.get("osascript") or "/usr/bin/osascript"
    applescript_path = "{packages_dir}/RailsTest/rails_test.applescript".format(
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
    test_name = self.test_name_from_text(True)
    if not test_name:
      # otherwise cursor is above first test, so get the first test name after
      test_name = self.test_name_from_text(False)
    self.run_tests(test_name)


  def test_name_from_text(self, reverse_lookup):
    test_name = None
    view = self.window.active_view()
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
      test_name_match = re.match(r"^.*?def\s+(test_.+?)($|\s)", line)
      if test_name_match:
        test_name = test_name_match.group(1)
        break
    return test_name


class RailsTestCommand(RailsTestRunner, FindRailsFiles, sublime_plugin.WindowCommand):
  def run(self):
    self.run_tests()


class ToggleRailsTestFileCommand(FindRailsFiles, sublime_plugin.WindowCommand):
  def run(self):
    if not self.set_project_folder():
      return

    filepath = self.window.active_view().file_name()
    filename = os.path.basename(filepath)

    is_test_file, code_file = self.check_if_test_file(filename)
    if is_test_file:
      self.open_code_file(code_file)
    else:
      test_file = filename.replace('.rb', '') + '_test.rb'
      self.open_test_file(test_file)

