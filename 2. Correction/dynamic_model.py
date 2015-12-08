import math
import string
import build_char_confusion

# Dynamic model for document-specific correction

class DynamicModel():

	# Sweeps through raw sentences first to find relevant denominators, otherwise 1/1 = 100%
	def __init__(self, raw_sentences, smoothing, enable_dict, enable_context, enable_conf):
		self.smoothing = smoothing
		self.enable_dict = enable_dict
		self.enable_conf = enable_conf
		self.enable_context = enable_context

		# Counts for proper nouns
		self.proper_noun_count = {}       # Counts proper nouns 
		self.proper_noun_map = {}         # Maps proper noun to its potential correct spelling 
		self.proper_noun_list = set([])   # Assumed list of unique, correctly-spelled proper nouns

		# Counts for initial model
		self.sentence_count = len(raw_sentences)
		self.i_count = {}

		# Counts for transition model
		self.t_pair_count, self.dict_count = {}, {}
		self.total_t_count = 0

		# Counts for confusion model
		self.total_c_count = 0
		self.c_count, self.count_ins, self.count_del, self.count_sub = {}, {}, {}, {}

		if self.enable_dict or self.enable_conf or self.enable_context: 
			print("Initiatizing dynamic model...")
			# Initializes dictionary counts and denominators only
			for i, sentence in enumerate(raw_sentences):
				if self.enable_context: self.total_t_count += len(sentence) - 1  # Count number of possible (w1, w2) pairs
				for s in sentence:
					if self.enable_dict and self.is_proper_noun(s) and i != 0: self.increment_dict(self.proper_noun_count, s.lower())
					s = s.lower()
					if self.enable_context: self.increment_dict(self.dict_count, s) 
					if self.enable_conf:
						self.total_c_count += len(s)                   # Count total number of characters, as approx for corrected text
						for c in s:
							self.increment_dict(self.c_count, c)       # Count frequent of character, as approx for corrected text

		if self.enable_dict:
			pnouns = [(pn, self.proper_noun_count[pn]) for pn in self.proper_noun_count.keys()]
			pnouns.sort(key=lambda elem: elem[1], reverse=True)
			for i, (pn, freq) in enumerate(pnouns):
				if pn not in self.proper_noun_map.keys() and freq >= 10: # haven't been assigned to a PN with higher freq
					self.proper_noun_list.add(pn)
					for j in range(i + 1, len(pnouns)): # compare with all PNs of lower frequency
						pn2 = pnouns[j][0]
						if pn2 not in self.proper_noun_map.keys(): # Don't need to test if already matched with another	
							if (('’' in pn) == ('’' in pn2)) and self.levenshtein(pn, pn2) <= 2: # Consider match if <= 2 distance and has/hasn't apostrophe
								self.proper_noun_map[pn2] = pn
							elif ('’' not in pn) and ('’' in pn2): # Handles apostrophe cases
								pn3 = pn2[:pn2.index('’')]
								if self.levenshtein(pn, pn3) <= 2:
									self.proper_noun_map[pn3] = pn


	# Increment or decrement dictionary if key exists. Otherwise, only initialize key if increment
	# Once count goes to zero from decrementing, has option to remove key
	def increment_dict(self, d, k, incr = 1.0, remove = False):
		if k in d.keys():
			d[k] += incr
			if d[k] < 0: # Shouldn't get here
				print("Negative count in dictionary... " + str(k))
				input()
			if d[k] == 0 and remove: # For dict_count, remove if all occurences of word was actually wrong
				d.pop(k)
		else:
			if incr >= 0:
				d[k] = incr
			else: # Shouldn't get here
				print("Decrementing unfound key in dictionary... " + str(k))
				input()


	# Returns initial probabilities based on initial model built so far
	def i_prob(self, ik, wgt):
		if self.enable_context:
			ikeys = self.i_count.keys()
			if ik in ikeys:
				return wgt * math.log((self.i_count[ik] + self.smoothing)/(self.sentence_count + (len(ikeys) + 1)*self.smoothing))
			else:
				return wgt * math.log(self.smoothing/(self.sentence_count + (len(ikeys) + 1)*self.smoothing))
		else:
			return None

	# Returns transition probabilities based on transition model built so far; tk = (w1, w2)
	def t_prob(self, tk, wgt):
		if self.enable_context:
			if tk in self.t_pair_count.keys() and tk[0] in self.dict_count.keys():
				return wgt * math.log((self.t_pair_count[tk] + self.smoothing)/(self.dict_count[tk[0]] + len(self.dict_count.keys())*self.smoothing))
			else:
				return wgt * math.log(self.smoothing/self.total_t_count) ################################ TO DO ####################################
		else:
			return None


	# Returns ins, del, and sub probabilities for use in emission probability calculation
	def chr_ins_prob(self, c, wgt):
		if self.enable_conf:
			if c in self.count_ins.keys():
				return wgt * math.log(self.count_ins[c] / self.total_c_count)
			else:
				return wgt * math.log((1 - self.smoothing) / self.total_c_count)
		else:
			return None

	def chr_del_prob(self, c, wgt):
		if self.enable_conf:
			if c in self.count_del.keys() and c in self.c_count.keys():
				return wgt * math.log(self.count_del[c] / self.c_count[c])
			else:
				return wgt * math.log((1 - self.smoothing) / self.total_c_count)
		else:
			return None

	def chr_sub_prob(self, s, w, wgt):
		if self.enable_conf:
			if (s, w) in self.count_sub.keys() and w in self.c_count.keys():
				return wgt * math.log(self.count_sub[(s, w)] / self.c_count[w])
			else:
				if s == w:
					return wgt * math.log(self.smoothing)
				else:
					return wgt * math.log((1 - self.smoothing) / self.total_c_count)
		else:
			return None


	# Correct for document-generated proper nouns; param will not be first word in sentence
	# Only correct words that fit proper noun criteria, for damage control in case error
	def correct_pnoun(self, w):
		if self.enable_dict:
			if self.is_proper_noun(w) and w.lower() in self.proper_noun_map.keys():
				w = w.lower()
				if '’' in w:
					if w in self.proper_noun_map.keys():
						return self.proper_noun_map[w]
					else:
						root = w[:w.index('’')]
						return w.replace(root, self.proper_noun_map[root])
				else:
					return self.proper_noun_map[w]
			else:
				return w
		else:
			return None


	# Updates models based on latest sentence corrected
	def update(self, sentence_obs, sentence_act):
		if self.enable_conf or self.enable_context: print("Updating dynamic model for sentence...")

		prec = None
		for (s, w) in zip(sentence_obs, sentence_act):
			s = s.lower()
			w = w.lower()
			# Update initial and transition counts
			if self.enable_context:
				if prec == None:                               # update initial count
					self.increment_dict(self.i_count, w)
					prec = w
				else:                                          # update transition counts
					if s != w:
						self.increment_dict(self.dict_count, s, incr = -1.0, remove = True) # Undo previous assumption
						self.increment_dict(self.dict_count, w)                             # Adjust previous assumption
					self.increment_dict(self.t_pair_count, (prec, w))
					prec = w

			# Update confusion counts. Adjust char count assumptions from initial ocr output
			if self.enable_conf and s.islower(): # Only run if no capital letters
				self.total_c_count += (-len(s) + len(w))                      # Adjust previous assumption
				ops = list(build_char_confusion.needleman_wunsch_ops(s, w))
				for op, chrs in ops:
					if op == "sub":
						self.increment_dict(self.count_sub, (chrs[0], chrs[1]))
						self.increment_dict(self.c_count, chrs[0], incr = -1.0) # Undo previous assumption
						self.increment_dict(self.c_count, chrs[1])
					elif op == "ins":
						self.increment_dict(self.count_ins, chrs)
						self.increment_dict(self.c_count, chrs, incr = -1.0) # Undo previous assumption
					elif op == "del":
						self.increment_dict(self.count_del, chrs)
						self.increment_dict(self.c_count, chrs)              # Adjust previous assumption
	

	def is_proper_noun(self, w):
		return (len(w) >= 5 and w[0].upper() == w[0] and w[0].isalpha())


	def levenshtein(self, s1, s2):
	    if len(s1) < len(s2):
	        return self.levenshtein(s2, s1)

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