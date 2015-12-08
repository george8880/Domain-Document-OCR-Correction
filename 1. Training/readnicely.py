import csv
import sys
import itertools
import glob
import os

def read_alphanum(file_path):
	alphanum = "abcdefghijklmnopqrstuvwxyz1234567890"
	result = []

	with open(file_path, 'r', errors = "ignore") as f: # Mansfield: encoding = 'iso-8859-15'
		for line in f:
			tok = line.strip()
			if not (len(tok) == 1 and tok.lower() not in alphanum):
				result.append(tok)

	return result


files_f = [sys.argv[2] + "_f.txt"] if sys.argv[2] != "all" else [os.path.basename(x) for x in glob.glob(sys.argv[1] + '/Tokens/*_f.txt')]
files_i = [sys.argv[2] + "_i.txt"] if sys.argv[2] != "all" else [os.path.basename(x) for x in glob.glob(sys.argv[1] + '/Tokens/*_i.txt')]
file_pairs = zip(sorted(files_i), sorted(files_f))

for i_file, f_file in file_pairs:
	filename = i_file[:-6]
	print("Doing: " + filename)

	tokens_i = read_alphanum(sys.argv[1] + "/Tokens/" + i_file)
	tokens_f = read_alphanum(sys.argv[1] + "/Tokens/" + f_file)

	outputCsvFile = open(sys.argv[1] + "/Aligned/" + filename + "_align_raw.csv", 'wt', newline = '')
	writer = csv.writer(outputCsvFile)

	for (tok_i, tok_f) in itertools.zip_longest(tokens_i, tokens_f, fillvalue="<null>"):
		writer.writerow([tok_i, tok_f])

