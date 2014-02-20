global ruby_initialization, project_folder, test_file, test_name, subtest_group

on run argv
	if (count of argv) is 0 then
		--DEBUGGING USE IN APPLESCRIPT EDITOR
		set ruby_initialization to "19"
		set project_folder to "/Users/btsai/git/workcloud/workcloud"
		set test_file to "test/unit/company_test.rb"
		set test_name to "test_display_name"
		set subtest_group to null
	else
		--SHOULD HAVE 3 + 2 OPTIONAL ARGUMENTS PASSED OVER BY SUBLIME SCRIPT
		set ruby_initialization to item 1 of argv
		set project_folder to item 2 of argv
		set test_file to item 3 of argv
		set test_name to null
		set subtest_group to null
		if (count of argv) is 4 then
			set test_name to item 4 of argv
		else if (count of argv) is 5 then
			set test_name to item 4 of argv
			set subtest_group to item 5 of argv
		end if
	end if
	
	tell application "iTerm"
		set session_name to the last word in test_file
		if test_name is not null then
			set session_name to session_name & "-" & test_name
		end if
		
		set test_session to my existing_session_named(session_name)
		if test_session is null then
			set test_session to my new_session_named(session_name, ruby_initialization, project_folder)
		end if
		
		select test_session
		tell test_session
			activate
			
			if my is_in_repeat_mode(test_session) then
				set test_command to "y"
			else
				if subtest_group is not null then
					set test_command to "ONLY=" & subtest_group & " "
				else
					set test_command to ""
				end if
				set test_command to test_command & "ruby " & test_file & ""
				if test_name is not null and test_name is not "none" then
					set test_command to test_command & " -n " & test_name
				end if
				set test_command to test_command & " -o"
			end if
			
			write text test_command
		end tell
		
	end tell
	
end run

on is_in_repeat_mode(_session)
	set last_line to my last_line_in_session(text of _session)
	if last_line is "Do you want to run this suite again [y/n]?" then
		return true
	else
		return false
	end if
end is_in_repeat_mode

on last_line_in_session(buffer_text)
	set last_line to null
	set session_lines to reverse of every paragraph of buffer_text
	repeat
		set first_word to first item of session_lines
		if first_word is "" then
			set session_lines to rest of session_lines
		else
			set last_line to first_word
			exit repeat
		end if
	end repeat
	return last_line
end last_line_in_session

on existing_session_named(name_to_find)
	tell application "iTerm"
		set test_session to null
		repeat with _session in every session of the current terminal
			if my session_is_named(_session, name_to_find) then
				set test_session to _session
				exit repeat
			end if
		end repeat
		return test_session
	end tell
end existing_session_named

on new_session_named(new_name)
	tell application "iTerm"
		tell the current terminal
			launch session "Default Session"
			set name of current session to new_name
			tell current session
				activate
				write text ruby_initialization
				write text "cd " & project_folder & ""
			end tell
			return current session
		end tell
	end tell
end new_session_named

on session_is_named(_session, name_to_find)
	set _session_name to name of _session
	set match_length to length of name_to_find
	if length of _session_name ³ match_length then
		set base_name to text 1 thru match_length of _session_name
		if base_name is name_to_find then
			return true
		end if
	end if
	return false
end session_is_named


