## Toggle Rails Test File

Simple plugin and key binding (Cmd + .) to toggle between a Rails model / lib file or controller file and its related unit or functional test.


## Run Rails Test File

This is specific to the repeating minitest runner setup.

Run your current test suite (cmd+k, cmd+t, cmd+a) or current test where the cursor is (cmd+k, cmd+t, cmd+t).

If you are on a model and there is a matching test file, it will open and run the test file.

Each test suite or specific test name will map to its own tab in iTerm, so that one there is a matching tab, every time you run the test, it will find and run the test in the same tab.


## Installation

Sorry, I'm not pushing these through PackageControl so just clone to your Library/Application Support/Sublime/Packages folder.

