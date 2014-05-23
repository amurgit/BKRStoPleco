# -*- coding: utf-8 -*-
import re
import time
import sys
import operator


def show_progress(cur_index, max_index):
    if max_index <= 0:
        max_index = self.params['approx_count_of_words']
    if cur_index%(int(max_index/100)) == 0:
        log('Working... '+str(cur_index*100/max_index)+'%')

def log(message):
    message = message.encode('utf-8')
    con_time = time.strftime('%H:%M:%S')
    print con_time+'    '+message

def filter_hanzi(hanziword):
    clean_word = ''
    for char in re.findall(ur'[\u3300-\u33FF\u3400-\u4DBF\u4e00-\u9fff\uF900-\uFAFF\uFE30-\uFE4F]+', hanziword):
        clean_word = clean_word+char
    clean_word = clean_word.replace(u'﹐', '')
    clean_word = clean_word.replace(u'，', '')
    return clean_word

params = {
    'input_bkrs_file':        'dabkrs_140308.txt',
    'output_freq_file':        'char-frequency.txt',
    'approx_count_of_words':  2500000,
}

dic = open(params['input_bkrs_file'], mode='r')
freqfile = open(params['output_freq_file'], mode='w')
hanzi_stat = {}
line_type = ''
word = ''
pronounce = ''
translate = ''
word_index = 0
for line in dic:
            if line == '\n':
                line_type = 'word'
            else:
                if not line.startswith('#'):
                    if line_type == 'word':
                        word_index = word_index+1
                        show_progress(word_index, params['approx_count_of_words'])
                        word = (line[:-1]).strip().decode('utf-8')
                        line_type = 'pronounce'
                    elif line_type == 'pronounce':
                        pronounce = (line[1:-1]).strip().decode('utf-8')
                        line_type = 'translate'
                    elif line_type == 'translate':
                        clean_word = filter_hanzi(word)
                        for hanzi in clean_word:
                            try:
                                hanzi_stat[hanzi]['count'] += 1
                            except KeyError:
                                hanzi_stat[hanzi] = {'hanzi': hanzi, 'count':1}

hanzilist = []
for key, val in hanzi_stat.items():
    hanzilist.append(val)
uniquehanzi = len(hanzilist)
hanzilist.sort(key=lambda x: x['count'], reverse = True)
for hanzi in hanzilist:
    freqfile.write(hanzi['hanzi'].encode('utf-8')+'\t'+str(hanzi['count'])+'\n')

freqfile.close()
dic.close()