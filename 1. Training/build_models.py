import glob
import nltk
import string
import math
import sys

# Read tokens from already tokenized file
def read_toks(file_path):
	print("Reading tokens from: " + file_path)
	return [line.rstrip('\n') for line in open(file_path, 'r', errors = "ignore")]

# Creates an array of tokenized files
def tokenize_library(file_list):
	print("Creating token library.................")
	return [read_toks(f) for f in file_list]


# Writes dictionary to output_file_path in the format: key value
def write_file(d, output_file_path, transition_model = False, array = False):
	print("Writing model to: " + output_file_path)
	with open(output_file_path, 'wt') as f:
		if not array:
			for k, v in d.items():
				if transition_model:
					f.write(str(k[0]) + " " + str(k[1]) + " " + str(v) + "\n")
				else:
					f.write(str(k) + " " + str(v) + "\n")
		else:
			for v in d:
				f.write(str(v) + "\n")


# If k exists in d, increment value; otherwise, initialize as 1
def increment_dict(d, k):
	d[k] = 1.0 if k not in d else d[k] + 1.0

# Turns list of tokens into list of sentences, using end_punct as delimiters
def sentencizer(toks):
	end_punct, result, temp = '—.?/!;\"', [], []

	for t in toks:
		if t in end_punct and temp:
			result.append(list(temp))
			temp = []
		elif t not in string.punctuation:
			temp.append(t)
	return result


##############################################s
# Dictionary: list of all words in training  #
#                                            #
# Emission Model:                            #
# Calculates and writes: W_i log(prob)       #
#                                            # 
# Transition Model:                          #
# Calculates and writes: W_i-1 W_i log(prob) #
##############################################
def main_model(tokenized_library, smoothing):
	print("Counting............")

	i_count, t_count, total_t_count = 0, {}, 0
	i_prob, t_prob = {}, {}
	d = set([])

	for tokenized_file in tokenized_library:
		sentences = sentencizer(tokenized_file)

		for s in sentences:
			first_tok, prev_tok = True, None
			for t in s:
				tok = t.lower()
				if first_tok: # Assign initial counts
					increment_dict(i_prob, tok)
					i_count += 1
					first_tok = False
				else: # Assign transition counts
					increment_dict(t_prob, (prev_tok, tok))
					increment_dict(t_count, prev_tok)
					total_t_count += 1

				if tok not in d:
					d.add(tok)
				prev_tok = tok

	print("Calculating probabilities............")
	k, ikeys, tkeys = 1, i_prob.keys(), t_prob.keys()
	for ik in ikeys: i_prob[ik] = math.log((i_prob[ik] + smoothing)/(i_count + (len(ikeys) + 1)*smoothing))
	for tk in tkeys: t_prob[tk] = math.log((t_prob[tk] + smoothing)/(t_count[tk[0]] + len(d)*smoothing))
	i_prob["<UNK>"] = math.log(smoothing/(i_count + (len(ikeys) + 1)*smoothing))
	t_prob[("<UNK>", "<UNK>")] = math.log(smoothing/total_t_count) ################################ TO DO ####################################

	write_file(i_prob, "./" + sys.argv[1] + "/initial_model.txt")
	write_file(t_prob, "./" + sys.argv[1] + "/transition_model.txt", transition_model = True)
	write_file(d, "./" + sys.argv[1] + "/dict.txt", array = True)


#----------------Get training files list----------------
directory = './' + sys.argv[1] + '/Tokens/*_f.txt'
text_files_f = glob.glob(directory)
print("Training models from: " + directory)

#----------------Tokenize training files----------------
lib = tokenize_library(text_files_f)

main_model(lib, 1e-10)