import automata
import math
import string
import sys
import dynamic_model
from optparse import OptionParser

# SYS ARGS: Domain/General, FILENAME, OUTPUT FILENAME

class Viterbi():

	# Enable_[ ] creates dynamic, document-specific models in addition to trained models
	# k is the error margin for candidate selection
	def __init__(self, raw_filename, d, output_filename, k, enable_dict, enable_context, enable_conf):
		self.dir = d
		self.enable_dict = enable_dict
		self.enable_context = enable_context
		self.enable_conf = enable_conf
		self.k = k

		self.raw_sentences = self.sentencizer(self.import_raw_tokens(raw_filename))
		self.dm = dynamic_model.DynamicModel(self.raw_sentences, 1e-10, enable_dict = self.enable_dict, enable_context = self.enable_context, enable_conf = self.enable_conf)

		self.import_models()
		#if self.enable_dict: # Augment dictionary by proper nouns, if enabled
		#	self.d = self.d.union(self.dm.proper_noun_list)
		#	self.m = automata.Matcher(list(self.d))
		#else:
		self.m = automata.Matcher(self.words)	

		# Memoization for candidate list of words and for emission probability
		# Refreshed every sentence for dynamically updating models
		# Or not refreshed at all for static models
		self.memoize_em, self.memoize_can = {}, {}

		self.write_corrected(output_filename)


	def import_raw_tokens(self, filename):
		print("Reading tokens from: " + filename)
		return [line.rstrip('\n') for line in open(filename, 'r', errors = "ignore")]


	# Turns list of tokens into list of sentences, using end_punct as delimiters
	def sentencizer(self, toks):
		end_punct, result, temp = '—.?/!;\"', [], []

		for t in toks:
			if t in end_punct and temp:
				result.append(list(temp))
				temp = []
			elif t not in string.punctuation:
				temp.append(t)
		return result


	# Read pre-calculated models in current folder
	def import_models(self, d_loc = 'dict.txt', i_loc = 'initial_model.txt', t_loc = 'transition_model.txt', ce_loc = 'char_edit_model.txt'):
		# Read dict.txt
		self.words = None
		with open(self.dir + "/" + d_loc,'r') as f:
			self.words = [word.rstrip('\n') for word in f.readlines()]
		self.words.sort()
		self.d = set(self.words)

		# Read initial_model.txt
		self.i_prob = {}
		with open(self.dir + "/" + i_loc,'r') as f:
			for line in f.readlines():
				toks = line.split()
				self.i_prob[toks[0]] = float(toks[1])

		# Read transition_model.txt
		self.t_prob = {}
		with open(self.dir + "/" + t_loc,'r') as f:
			for line in f.readlines():
				toks = line.split()
				self.t_prob[(toks[0], toks[1])] = float(toks[2])

		# Read char_edit_model.txt
		self.chr_ins_prob = {}
		self.chr_del_prob = {}
		self.chr_sub_prob = {} # (a, b): character b is recognized by OCR as character a
		with open(self.dir + "/" + ce_loc,'r') as f:
			for line in f.readlines():
				toks = line.split()
				if toks[0] == "INS":
					self.chr_ins_prob[toks[1]] = float(toks[2])
				elif toks[0] == "DEL":
					self.chr_del_prob[toks[1]] = float(toks[2])
				elif toks[0] == "SUB":
					self.chr_sub_prob[(toks[1], toks[2])] = float(toks[3])


	# Given observation, return a list of candidate replacement words from dictionary words
	# Using Levenshtein Automata with minimum editing distance 3
	# Rank by emission probability, and only return top N (<= 10) most likely candidates
	def candidates_for(self, obs, N = 10):
		if self.enable_dict and obs in self.dm.proper_noun_list:
			return [obs]

		if obs in self.d: # don't need to find candidates if valid word already
			return [obs]
		elif obs in self.memoize_can.keys():
			return self.memoize_can[obs]
		else:
			candidates = list(automata.find_all_matches(obs, self.k, self.m))
			if len(candidates) == 0:
				self.memoize_can[obs] = [obs]
			else:
				can_prob = [(c, self.emission_prob(obs, c)) for c in candidates]
				if self.enable_dict: can_prob.append((obs, self.emission_prob(obs, obs)))
				can_prob.sort(key = lambda x: x[1], reverse = True) # rank candidates by higher probability
				self.memoize_can[obs] = [can_prob[i][0] for i in range(min(N, len(can_prob)))]

			return self.memoize_can[obs]


	# Returns the probability that given word w, the OCR returns observed word s
	# Uses character-level editing probabilities
	# If enable_conf, then include document-specific character confusion estimates as well
	def emission_prob(self, s, w):
		if (s, w) in self.memoize_em.keys():
			return self.memoize_em[(s, w)]
		else:
			ls, lw = len(s), len(w)

			# tlb[(i, j)] = probability that substring w(0..j) is recognized by OCR as substring s(0..i)
			tbl = {}
			tbl[(-1, -1)] = 0

			for i in range(ls):
				tbl[(i, -1)] = tbl[(i - 1, -1)] + (self.chr_ins_prob[s[i]] if s[i] in self.chr_ins_prob.keys() else -10) + (self.dm.chr_ins_prob(s[i], self.dynamic_weight) if self.enable_conf else 0)
			for j in range(lw): 
				tbl[(-1, j)] = tbl[(-1, j - 1)] + (self.chr_ins_prob[w[j]] if w[j] in self.chr_ins_prob.keys() else -10) + (self.dm.chr_ins_prob(w[j], self.dynamic_weight) if self.enable_conf else 0)

			for i in range(ls):
				for j in range(lw):
					insertion = tbl[(i - 1, j)] + (self.chr_ins_prob[s[i]] if s[i] in self.chr_ins_prob.keys() else -10) + (self.dm.chr_ins_prob(s[i], self.dynamic_weight) if self.enable_conf else 0)
					deletion = tbl[(i, j - 1)] + (self.chr_del_prob[w[j]] if w[j] in self.chr_del_prob.keys() else -10) + (self.dm.chr_del_prob(w[j], self.dynamic_weight) if self.enable_conf else 0)
					substitution = tbl[(i - 1, j - 1)] + (self.chr_sub_prob[(s[i], w[j])] if (s[i], w[j]) in self.chr_sub_prob.keys() else -10) + (self.dm.chr_sub_prob(s[i], w[j], self.dynamic_weight) if self.enable_conf else 0)
					tbl[i,j] = max(insertion, deletion, substitution)

			self.memoize_em[(s, w)] = tbl[ls - 1, lw - 1]
			return self.memoize_em[(s, w)]


	# Returns (max, arg max) for an array
	def maxp_argmax(self, arr):
		maxp, argmax = None, ""
		for word, prob in arr: 
		    if maxp == None or prob > maxp: 
		    	maxp, argmax = prob, word
		return (maxp, argmax)


	def correct_sentence(self, raw_sentence):
		delta, psi, candidates = {}, {}, {} 
		sentence = [w for w in raw_sentence]

		# Document-specific proper noun correction, if enabled, + lower()
		# Only correct if not first word and not in trained dictionary
		# Proper noun criteria check is on correct_pnoun side
		for i, w in enumerate(sentence):
			if self.enable_dict and w.lower() not in self.d and i != 0:
				sentence[i] = self.dm.correct_pnoun(w)
			sentence[i] = sentence[i].lower()

		# Initialize
		delta[0] = {}
		first_word = sentence[0]
		candidates[0] = self.candidates_for(first_word)
		for c in candidates[0]:
		    ip = (self.i_prob["<UNK>"] if c not in self.i_prob else self.i_prob[c]) + (self.dm.i_prob(c, self.dynamic_weight) if self.enable_context else 0)
		    ep = self.emission_prob(first_word, c)
		    delta[0][c] = ip + ep

		# Induction
		for t in range(1,len(sentence)):
			curr_word = sentence[t]
			delta[t], psi[t] = {}, {}
			candidates[t] = self.candidates_for(curr_word)
			for j in candidates[t]:
				ep = self.emission_prob(curr_word, j)
				arr = [(i, delta[t-1][i] + (self.t_prob[("<UNK>", "<UNK>")] if (i, j) not in self.t_prob else self.t_prob[(i, j)]) + (self.dm.t_prob((i, j), self.dynamic_weight) if self.enable_context else 0)) for i in candidates[t-1]]
				maxp, argmax = self.maxp_argmax(arr)
				delta[t][j] = maxp + ep
				psi[t][j] = argmax

		# Termination
		arr = [(i, delta[len(sentence)-1][i]) for i in candidates[len(sentence)-1]]
		p_star, q_star = self.maxp_argmax(arr)

		# Result
		result = ["" for i in range(len(sentence))]
		result[len(sentence) - 1] = q_star
		for i in range(1, len(sentence)):
			t = len(sentence) - 1 - i
			result[t] = psi[t+1][result[t+1]]

		# If dynamic, update models for newly corrected sentence 
		if self.enable_context or self.enable_conf: 
			self.dm.update(raw_sentence, result)
			if self.enable_conf: # only need to wipe if dynamic confusion model
				self.memoize_em = {}

		return result


	def write_corrected(self, filename):
		total = len(self.raw_sentences)
		with open(filename, 'wt') as f:
			for i, s in enumerate(self.raw_sentences):
				self.dynamic_weight = i * 1.0 / total
				print("Correcting Sentence " + str(i + 1) + " of " + str(total))
				f.write(" ".join(self.correct_sentence(s)) + " \n")

parser = OptionParser()
parser.add_option("--dir", dest="dir", help="directory of models to use")
parser.add_option("--in", dest="in_f", help="input filename")
parser.add_option("--out", dest="out_f", help="output filename")
parser.add_option("-k", dest="k", default=3, help="margin for candidate selection, default 3")
parser.add_option("--enable_dict", action="store_true", dest="enable_dict", 
				  default=False, help="enable document-specific dictionary")
parser.add_option("--enable_context", action="store_true", dest="enable_context", 
				  default=False, help="enable dynamic context models")
parser.add_option("--enable_conf", action="store_true", dest="enable_conf", 
				  default=False, help="enable dynamic confusion models")
(options, args) = parser.parse_args()

v = Viterbi(options.in_f, options.dir, options.out_f, options.k, options.enable_dict, options.enable_context, options.enable_conf)