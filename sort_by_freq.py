# -*- coding: utf-8 -*-
from bkrs2pleco import BKRS2DB

bkrs = BKRS2DB(configfile = 'input_files/test/config.ini')
bkrs.load_character_frequency()
input_file = open('input_files/similar_hanzi.txt')
output_file = open('output_files/sorted_similar_hanzi.txt', 'w')

def line_freq(sline):
	freq = bkrs.get_hanzi_freq(sline.split('\t')[0].decode('utf-8'))
	#print sline.split('\t')[0]

	return freq

hanzi_lines = []
allhanzi = []
alllists = []
for line in input_file:
	line = line.replace('﻿','')
	uline = line.strip().decode('utf-8')
	hanzi_list = uline.split('\t')
	hanzi_list = list(set(hanzi_list))
	if len(hanzi_list) <=1:
		continue
	hanzi_list.sort(key=bkrs.get_hanzi_freq)
	hanzi_list.reverse()
	if not hanzi_list in alllists:
		alllists.append(hanzi_list)

for hanzi_list in alllists:
	newline = ''
	for hanzi in hanzi_list:
		if not hanzi in allhanzi:
			allhanzi.append(hanzi)
		else:
			print 'Dublicate: '+hanzi.encode('utf-8')
		newline = newline+hanzi.encode('utf-8')+'\t'
	newline = newline.strip('\t')
	hanzi_lines.append(newline)

#hanzi_lines.sort(key=line_freq)
#hanzi_lines.reverse()
#for l in hanzi_lines:
	#print line_freq(l)
output_file.write('\n'.join(hanzi_lines))