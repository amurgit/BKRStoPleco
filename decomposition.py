# -*- coding: utf-8 -*-
from __future__ import division
from cjklib import characterlookup
from bkrs2pleco import BKRS2DB

bkrs = BKRS2DB(configfile = 'input_files/test/config.ini')
bkrs.load_character_frequency()
bkrs.load_additional_pronounces()
cjk = characterlookup.CharacterLookup('T')
outfile = open('output_files/radicals_sorted.txt', 'w')
outfile2 = open('output_files/radicals_pinyin.txt', 'w')

def get_decomp(hanzi):
	obdec = cjk.getDecompositionEntries(hanzi)
	declist = []
	declist.append(hanzi)
	if not obdec:
		return declist
	for dec in obdec[0]:
		declist.append(dec[0])
	return declist
print 'step 0'
def get_frequent_hanzi(count=5000):
	freq_file = open('input_files/frequency.txt')
	freq = []
	i = 0
	for line in freq_file:
		line = line.replace('﻿','') # replace one not printable symbol
		uline = line.strip().decode('utf-8')
		hanzi = uline.split('\t')[0].strip()
		freq.append(hanzi)
		i += 1
		if i>=count:
			return freq

def sortkey(elem):
	return elem['count']

def sortkey2(rad):
	return rad['max_rel']

def get_all_pron_without_tone(hanzi):
	pronvars = bkrs.get_all_pron_variants(hanzi)
	clear_prons = []
	for pron_var in pronvars:
		clear_pron = bkrs.get_without_tone_mark(pron_var)
		clear_prons.append(clear_pron)
	clear_prons = list(set(clear_prons))
	return clear_prons

def len_sortkey(elem):
	return len(elem['hanzi'])

def group_hanzi_by_pron(hanzilist):

	hanzi_by_pron_ob = {}
	hanzi_by_pron_list = []
	for hanzi in hanzilist:
		prons = get_all_pron_without_tone(hanzi)
		for pron in prons:
			if not pron in hanzi_by_pron_ob:
				hanzi_by_pron_ob[pron] = {'pron': pron, 'hanzi': [hanzi]}
			else:
				hanzi_by_pron_ob[pron]['hanzi'].append(hanzi)
	for hbp in hanzi_by_pron_ob:
		hanzi_by_pron_list.append( hanzi_by_pron_ob[hbp])
	hanzi_by_pron_list.sort(key = len_sortkey)
	hanzi_by_pron_list.reverse()
	hbp_filtered = []
	all_hanzi = []
	for hbp in hanzi_by_pron_list:
		hanzi_list = []
		for hanzi in hbp['hanzi']:
			if not hanzi in all_hanzi:
				hanzi_list.append(hanzi)
		all_hanzi += hanzi_list 
		if hanzi_list:
			hbp_filtered.append({'pron':hbp['pron'], 'hanzi':hanzi_list})

	return hbp_filtered

freq = get_frequent_hanzi(count = 5000)
radicals_stat = {}
radicals = {}
for hanzi in freq:
	decomp = get_decomp(hanzi)
	if len(decomp)>3:
		if decomp[1] == u'⿰':
			del decomp[2]
	for dec in decomp:
		if dec not in radicals:
			#print dec.encode('utf-8')
			radicals[dec] = {'radical': dec,'count': 1, 'hanzi': [hanzi],'prons': {}}
		else:
			radicals[dec]['count'] += 1
			radicals[dec]['hanzi'].append(hanzi)
			radicals[dec]['max_rel'] = 0

		pron_vars = get_all_pron_without_tone(hanzi)
		for pron in pron_vars:
			if not pron in radicals[dec]['prons']:
				radicals[dec]['prons'][pron] = {'pron': pron, 'count': 1}
			else:
				radicals[dec]['prons'][pron]['count'] += 1

decomp_types = [u'⿰', u'⿱', u'⿸', u'⿻', u'⿺', u'⿵', u'⿹', u'⿴', u'⿳', u'⿷', u'⿲', u'⿶']
print 'step 1'

###########################################################	write most frequent radicals
radlist = []
for rad in radicals:
	radlist.append(radicals[rad])
radlist.sort(key = sortkey)
radlist.reverse()
for rad in radlist:
	if rad['radical'] in decomp_types:
		continue
	hanziline = ''
	for hanzi in rad['hanzi']:
		hanziline += hanzi.encode('utf-8')
	outfile.write(rad['radical'].encode('utf-8')+'\t'+str(rad['count'])+'\t'+hanziline+'\n')

print 'step 2'
############################################################# calculate rel
for rad in radlist:
	hanzi_count = 0
	max_count = 0
	max_count_pron = ''
	for pron in rad['prons']:
		pcount = rad['prons'][pron]['count']
		hanzi_count += pcount
		if pcount > max_count:
			max_count = pcount
			max_count_pron = pron

	radicals[rad['radical']]['max_rel_pron'] = max_count_pron
	if max_count == 0:
		radicals[rad['radical']]['max_rel'] = 1
	else:
		radicals[rad['radical']]['max_rel'] = (rad['count']-max_count+1)/(max_count*max_count)

print 'step 3'		
#####################################################################
radlist = []
for rad in radicals:
	radlist.append(radicals[rad])

radlist.sort(key = sortkey2)
#radlist.reverse()
i = 0
for rad in radlist:
	if rad['radical'] in decomp_types:
		continue
	hanziline = ''
	hanzi_by_pron_list = group_hanzi_by_pron(rad['hanzi'])
	#print hanzi_by_pron
	for pron in hanzi_by_pron_list:
		hanziline += pron['pron'].encode('utf-8')+'['+str(len(pron['hanzi']))+']'
		for hanzi in pron['hanzi']:
			hanziline += hanzi.encode('utf-8')
		hanziline += '\t'
	if rad['max_rel']<=0.25:
		if rad['count'] >=5:
			#+'\t'+str(round(rad['max_rel'],5))
			outfile2.write(rad['radical'].encode('utf-8')+' ['+str(rad['count'])+']\t'+hanziline+'\n')
	#i += 1
	if i>100:
		break
