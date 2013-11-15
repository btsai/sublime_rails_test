import sublime, sublime_plugin, os, re, fnmatch

# utility commands for this plugin
class ToggleRailsTestFileCommand(sublime_plugin.WindowCommand):
    def run(self):
      self.project_folder = None if len(self.window.folders()) == 0 else self.window.folders()[0]
      if not self.project_folder:
        return

      filepath = self.window.active_view().file_name()
      filename = os.path.basename(filepath)

      testfile_check = re.match(r"^(.+?)_test\.rb", filename)
      if testfile_check: # is test
        code_file = testfile_check.group(1) + '.rb'
        if self.open_file_if_exists(self.model_path(code_file)):
          pass
        elif self.open_file_if_exists(self.controller_path(code_file)):
          pass
      else:     # is code
        test_file = filename.replace('.rb', '') + '_test.rb'
        if self.open_file_if_exists(self.unit_test_path(test_file)):
          pass
        elif self.open_file_if_exists(self.functional_test_path(test_file)):
          pass

    def open_file_if_exists(self, filepath):
        if filepath and os.path.exists(filepath):
          self.window.open_file(filepath)
        else:
          return False

    def model_path(self, filename):
      return self.recursive_find('app/models', filename)

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

    def recursive_glob(self, base_folder, pattern):
      results = []
      for base, dirs, files in os.walk(base_folder):
        goodfiles = fnmatch.filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
      return results
