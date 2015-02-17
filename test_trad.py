# -*- coding: utf-8 -*-
import re
import sqlite3
import time
import sys
import cjklib #http://cjklib.org/0.3/
import operator
from cjklib.reading import ReadingFactory 
from cjklib import characterlookup
from cjklib import cjknife
from cjklib.dictionary import CEDICT
from pleco import Pleco

def get_alt(chars, schar):
	print chars
	alt = chars[0]
	for char in chars:
		print alt.encode('utf-8')
		if char != schar:
			alt = char
	print alt.encode('utf-8')
	return alt

charInfo =  cjknife.CharacterInfo()

simp_word = u'红枪会'

tradchars = []
for schar in simp_word:
	tchar = get_alt(charInfo.getTraditional(schar)[0],schar)
	tradchars += tchar
tradword = ''.join(tradchars)

print tradword.encode('utf-8')

