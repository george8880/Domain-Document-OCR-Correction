import sys
import nltk
import glob
import os

# SYS ARGS: Domain / General, all_i / all_f

# Split file at file_path into array of words and punctuation
result = []
if sys.argv[2] == "all_i":
	files = [os.path.basename(x) for x in glob.glob(sys.argv[1] + '/Raw/*_i.txt')]
elif sys.argv[2] == "all_f":
	files = [os.path.basename(x) for x in glob.glob(sys.argv[1] + '/Raw/*_f.txt')]
else:
	files = [sys.argv[2]]

for filename in files:
	print("Starting to tokenize: " + filename)

	result = []

	with open(sys.argv[1] + "/Raw/" + filename,'r', errors='ignore') as f:
		for line in f:
			# print(line) #debug			
			for tok in nltk.word_tokenize(line.replace('—', ' — ').replace('--', ' — ')):
				if tok[0] == '\'' and len(tok) > 1: 
					tok = tok[1:] # handles quote in quote in text 

				# Accounts for - split of word between two lines (i.e. prop-\n erty)
				if len(result) > 0 and result[-1][-1] == '-':
					result[-1] = result[-1][:-1] + tok
				else:
					result.append(tok)

	with open(sys.argv[1] + "/Tokens/" + filename, 'wt', errors='ignore') as f:
		for tok in result:
			f.write(("\"" if tok == "\'\'" or tok == "``" else tok) + "\n")