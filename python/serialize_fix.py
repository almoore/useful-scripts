#!/usr/bin/env python

# *** TESTS ***
#returns properly formatted string
#doesnt lose any characters
#both escaped/nonescaped quotes work
#works with quotes (esc/nonesc) within string
#returns proper #
#correctly handles escape sequences

import os, re

# Regexp to match a PHP serialized string's signature
serialized_token = re.compile(r"s:(\d+)(:\\?\")(.*?)(\\?\";)")

# Raw PHP escape sequences
escape_sequences = (r'\n', r'\r', r'\t', r'\v', r'\"', r'\.')

# Return the serialized string with the corrected string length
def _fix_serialization_instance(matches):
  target_str = matches.group(3)
	ts_len = len(target_str)

	# PHP Serialization counts escape sequences as 1 character, so subtract 1 for each escape sequence found
	esc_seq_count = 0
	for sequence in escape_sequences:
		esc_seq_count += target_str.count(sequence)
	ts_len -= esc_seq_count

	output = 's:{0}{1}{2}{3}'.format(ts_len, matches.group(2), target_str, matches.group(4))
	return output

# Accepts a file or a string
# Iterate over a file in memory-safe way to correct all instances of serialized strings (dumb replacement)
def fix_serialization(file):
	try:
		with open(file,'r') as s:
			d = open(file + "~",'w')

			for line in s:
				line = re.sub(serialized_token, _fix_serialization_instance, line)
				d.write(line)

			d.close()
			s.close()
			os.remove(file)
			os.rename(file+'~',file)
			print "file serialized"
			return True
	except:
		# Force python to see escape sequences as part of a raw string (NOTE: Python V3 uses `unicode-escape` instead)
		raw_file = file.encode('string-escape')

		# Simple input test to see if the user is trying to pass a string directly
		if isinstance(file,str) and re.search(serialized_token, raw_file):
			output = re.sub(serialized_token, _fix_serialization_instance, raw_file)
			print output
			print "string serialized"
			return output
		else:
			print "Error Occurred: Not a valid input?"
			exit()

# EXAMPLES
# fix_serialization('s:2:\"http://murphy.psstudi\r\nosdev.com/wp-content/uploads/2013/03/logo-2.jpg\";')
# fix_serialization('test.txt')
# fix_serialization('texxxxt.txt')

if __name__ == "__main__":
	import sys

	try:
		fix_serialization(sys.argv[1])
	except:
		print "No File specified, use `python serialize_fix.py [filename]`"
