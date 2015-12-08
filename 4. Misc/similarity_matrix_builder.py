with open("similarity_matrix_raw.txt",'r') as f:
	m = [[x for x in line.rstrip('\n').split()] for line in f.readlines()]

print(m)
let = 'A'
with open("similarity_matrix_complete.txt",'wt') as f:
	for r in m:
		f.write("\'" + let + "\': {")
		let2 = 'A'

		for c in r:
			f.write("\'" + let2 + "\': " + str(c) + ", ")

			if let2 == 'Z':
				let2 = 'a'
			else:
				let2 = chr(ord(let2) + 1)

		f.write("},\n")
		if let == 'Z':
			let = 'a'
		else:
			let = chr(ord(let) + 1)