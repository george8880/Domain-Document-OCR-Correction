import sys
import glob
import os

def sum_arr(arr):
	sum = 0
	for v in arr:
		sum += v
	return sum

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def read_alphanum(file_path):
	alphanum = "abcdefghijklmnopqrstuvwxyz1234567890"
	result = []
	with open(file_path) as f:
		for line in f.readlines():
			tok = line.rstrip('\n')
			if not (len(tok) == 1 and tok not in alphanum):
				result.append(tok)
	return result


def write_aligned(file_path, result):
	with open(file_path, 'wt') as f:
		for ic, fc in result:
			f.write(ic + " " + fc + "\n")

##########################################################################################################

THRESHOLD = 2

result = []
files_f = [sys.argv[1] + "_f.txt"] if sys.argv[1] != "ALL" else [os.path.basename(x) for x in glob.glob('Tokens/*_f.txt')]
files_i = [sys.argv[1] + "_i.txt"] if sys.argv[1] != "ALL" else [os.path.basename(x) for x in glob.glob('Tokens/*_i.txt')]
file_pairs = zip(sorted(files_i), sorted(files_f))

print(files_f)
print(files_i)
input()

for i_file, f_file in file_pairs:

	# Load all tokens from that are not punctuation
	i_toks = read_alphanum("Tokens/" + i_file)
	f_toks = read_alphanum("Tokens/" + f_file)
	print("I: " + str(len(i_toks)) + "   F: " + str(len(f_toks)))
	input()

	# Matching time
	i = f = 0
	LIMIT = 3 # of words to look ahead
	TWOLIMIT = (2 * LIMIT + 1) # For for loops and stuff
	while (i < len(i_toks) and f < len(f_toks)):
		if i % 10000 == 0: print("I: " + str(i) + "   F: " + str(f))

		# words at current indicies don't match
		if levenshtein(i_toks[i], f_toks[f]) > THRESHOLD and i < len(i_toks) - TWOLIMIT and f < len(f_toks) - TWOLIMIT:
			# Check LIMIT words down i_file to see if OCR added anything extra
			check_i = [levenshtein(i_toks[j], f_toks[f]) for j in range(i + 1, i + TWOLIMIT)]
			sum_i = [sum_arr(check_i[m : m + LIMIT]) for m in range(LIMIT)] # index is 1 + idx from i

			# Check LIMIT words down f_file to see if OCR deleted anything
			check_f = [levenshtein(i_toks[i], f_toks[g]) for g in range(f + 1, f + TWOLIMIT)]
			sum_f = [sum_arr(check_f[m : m + LIMIT]) for m in range(LIMIT)] # index is 1 + idx from f

			# Pick index with lowest levenshtein sum over next 4 words
			i_match = None
			min_sum = 9999
			min_index = -1
			for idx, val in enumerate(sum_f):
				if val < min_sum:
					min_sum = val
					min_index = idx
					i_match = False
			for idx, val in enumerate(sum_i):
				if val < min_sum:
					min_sum = val
					min_index = idx
					i_match = True

			if i_match:
				for j in range(i, min_index):
					result.append((i_toks[j], "<null>"))
				i += min_index + 1
			else:
				for g in range(f, min_index):
					result.append(("<null>", f_toks[g]))
				f += min_index

		# words at current indicies either match, or already shifted per above
		result.append((i_toks[i], f_toks[f]))
		i += 1
		f += 1

	# All remaining toks
	if i < len(i_toks):
		for j in range(i, len(i_toks)):
			result.append((i_toks[j], "<null>"))
	else:
		for g in range(f, len(f_toks)):
			result.append(("<null>", f_toks[g]))

	write_aligned("Aligned/" + sys.argv[1] + "_aligned.txt", result)