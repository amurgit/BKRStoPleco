# -*- coding: utf-8 -*-
import re
import sqlite3
import time
import sys
import os
import cjklib #http://cjklib.org/0.3/
import operator
from cjklib.reading import ReadingFactory 
from cjklib import characterlookup
from cjklib import cjknife
from cjklib.dictionary import CEDICT
from pleco import Pleco
import ConfigParser
import statprof

class BKRS2DB(object):

    """Class to convert BKRS.info dictionary into Pleco database format"""
    def __init__(self, configfile):
        super(BKRS2DB, self).__init__()

        #statprof.start()

        self.get_config(configfile)
        self.comma_symbols = [u'，', u'﹐', ',']
        self.BUFFER_SIZE = 10000
        self.buffer_index = 0

        self.read_fab = ReadingFactory()
        self.cjk = characterlookup.CharacterLookup('T')
        self.pinyinOp = self.read_fab.createReadingOperator('Pinyin')
        self.charInfo =  cjknife.CharacterInfo()
        self.last_error = {'description':'', 'match':'', 'not_match': ''}
        self.bad_word_index = 0
        self.additional_reading = {}
        self.hanzi_stat = {}
        self.hanzi_freq = {}
        self.errors_description = {
            'pinyin_not_match':'Не совпадает', 
            'pinyin_have_tag_symbol':'В пиньине теги', 
            'pinyin_have_bad_symbol':'В пиньине плохие символы', 
            'pinyin_have_rus_letter':'В пиньине русские буквы',
            'pinyin_have_number_symbol':'В пиньине цифры',
            'word_have_alpha_symbol':'В слове alfa символы'
        }

        self.log_file = open(self.params['log_file'], 'w', 1000)
        if self.params['write_to_pleco_db']:
            self.pleco = Pleco(self.params['output_pleco_database_file'], self)
        
    def export(self):
        if self.params['write_to_db']:
            self.conn = sqlite3.connect(self.params['output_database_file'])
            self.cursor = self.conn.cursor()

        self.bad_words_file = open(self.params['bad_words_file'], 'w', 1000)
        self.bad_words_list = open(self.params['bad_words_list'], 'w', 100)
        self.bad_hanzi_list = open(self.params['bad_hanzi_list'], 'w', 100)
        self.start_bad_words_file()
        
        self.log('Start of export. Input: '+self.params['input_bkrs_file']+', output: '+self.params['output_pleco_database_file'])
        self.start_time = time.time()
 
        if self.params['write_to_db']:
            self.create_db()
        self.dic = open(self.params['input_bkrs_file'], mode='r')
        line_type = ''
        word = ''
        pronounce = ''
        translate = ''
        word_index = 0
        good_words = 0
        have_no_rus_translate = 0
        bad_word_not_found_pron_variant = 0
        pinyin_have_number_symbol = 0
        self.ambiguous_decomposition = 0
        pinyin_have_tag_symbol = 0
        num_pinyin_have_tone_mark = 0
        no_pron_symbols_in_pinyin = 0

        self.load_character_frequency()

        if self.params['additional_pronounces_file']:
            self.load_additional_pronounces()

        self.flog('Start work with BKRS data file...')
        for line in self.dic:
            if line == '\n':
                line_type = 'word'
            else:
                if not line.startswith('#'):
                    if line_type == 'word':
                        word_index = word_index+1
                        if self.params['show_progress']:
                            self.show_progress(word_index, self.params['to_word_number'])
                        word = (line[:-1]).strip().decode('utf-8')
                        #word = self.join_nonprintable_hanzi(word) # 鱼岁 = 鱥
                        line_type = 'pronounce'
                    elif line_type == 'pronounce':
                        pronounce = (line[1:-1]).strip().decode('utf-8')
                        line_type = 'translate'
                    elif line_type == 'translate':
                        if word_index <= self.params['from_word_number']:
                            continue
                        if self.params['to_word_number'] > 0:
                            if word_index >= self.params['to_word_number']:
                                break

                        translate = (line[1:-1]).strip().decode('utf-8')
                        translate_with_tags = translate
                        translate_pleco = self.pleco.remove_html_tags(translate)
                        word_info = ' line #'+str(word_index*4+1)+' word #'+str(word_index)+' word: '+word+' pinyin: '+pronounce
                        pronounce = self.filter_pinyin(pronounce)

                        if self.have_rus_letters(pronounce):
                            self.log('Warning: pinyin have russian letters'+word_info)
                            self.log_bad_word(word, pronounce, 'pinyin_have_rus_letter', translate_with_tags, word_index)
                            self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                            continue

                        if self.have_number_symbol(pronounce) and not self.have_number_symbol(word):
                            pinyin_have_number_symbol += 1
                            self.log('Pinyin have tone number '+word_info)
                            self.log_bad_word(word, pronounce, 'pinyin_have_number_symbol', translate_with_tags, word_index)
                            self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                            continue

                        if self.have_tag_symbol(pronounce):
                            pinyin_have_tag_symbol +=1
                            self.log('Warning: pinyin have tag symbols '+word_info)
                            self.log_bad_word(word, pronounce, 'pinyin_have_tag_symbol', translate_with_tags, word_index)
                            self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                            continue
                            
                        if not self.have_rus_letters(translate_pleco):
                            have_no_rus_translate += 1
                            continue

                        if self.have_pron_symbol(pronounce):
                            ob_pronounce = self.convert_full_pinyin(word, pronounce)
                            pronounce_numeric_tone = self.get_string_pron(ob_pronounce)
                            if not pronounce_numeric_tone:
                                self.log('Error not found pronounce variant'+word_info)
                                bad_word_not_found_pron_variant += 1
                                if self.last_error['description'] != 'HANZI_WITH_NO_PRON':
                                    if self.translate_have_rus(translate_with_tags):
                                        if self.have_lat_letters_or_numbers(word):
                                            self.log_bad_word(word, pronounce, 'word_have_alpha_symbol', translate_with_tags, word_index)
                                        else:
                                            self.log_bad_word(word, pronounce, 'pinyin_not_match', translate_with_tags, word_index)
                                        self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')              
                                continue
                        else:
                            no_pron_symbols_in_pinyin += 1
                            continue

                        if self.pinyin_have_bad_symbol(pronounce):
                            self.log_bad_word(word, pronounce, 'pinyin_have_bad_symbol', translate_with_tags, word_index)

                        trad_word = self.get_trad(word)

                        if self.params['write_to_pleco_db']:
                            self.pleco.write_db(word, trad_word, pronounce_numeric_tone, translate_pleco)
                            self.pleco.create_db_word_index(ob_pronounce, len(word))
                        if self.params['write_to_db']:
                            freq = self.get_word_freq(word)
                            self.write_db(trad_word, word, pronounce_numeric_tone, translate, freq)
                        self.clear_last_error()
                        good_words += 1

        self.flog('OK.. ###################################################################################')
        self.flog('Count of words:\t\t\t\t\t'+str(word_index))
        self.flog('Good words:\t\t\t\t\t\t'+str(good_words)+'\t\t('+str(round(float(good_words)*100/word_index,2))+'%)')
        self.flog('Have no rus translate:\t\t\t'+str(have_no_rus_translate)+'\t\t('+str(round(float(have_no_rus_translate)*100/word_index,2))+'%)')
        self.flog('Not found pronounce variant:  \t'+str(bad_word_not_found_pron_variant)+'\t\t('+str(round(float(bad_word_not_found_pron_variant)*100/word_index,2))+'%)')
        self.flog('Numeric pinyin have tone mark:\t'+str(num_pinyin_have_tone_mark)+'\t\t('+str(round(float(num_pinyin_have_tone_mark)*100/word_index,2))+'%)')
        self.flog('Pinyin field have tone number:\t'+str(pinyin_have_number_symbol)+'\t\t('+str(round(float(pinyin_have_number_symbol)*100/word_index,2))+'%)')
        self.flog('Pinyin pinyin have tag symbol:\t'+str(pinyin_have_tag_symbol)+'\t\t('+str(round(float(pinyin_have_tag_symbol)*100/word_index,2))+'%)')
        self.flog('Pinyin have no pron symbols:  \t'+str(no_pron_symbols_in_pinyin)+'\t\t('+str(round(float(no_pron_symbols_in_pinyin)*100/word_index,2))+'%)')
        self.log_hanzi_stat()

        if self.params['write_to_pleco_db']:
            self.pleco.create_db_index()
            self.pleco.conn.commit()
            self.pleco.conn.close()

        if self.params['write_to_db']:
            self.create_db_index()
            self.conn.commit()
            self.conn.close()

        self.dic.close()
        self.end_time = time.time()
        self.flog('End of export. Total time: '+str(round(self.end_time - self.start_time ,2))+' sec')
        
        self.end_bad_words_file()
        self.bad_words_list.close()
        self.bad_hanzi_list.close()
        self.bad_words_file.close()

        #statprof.stop()
        #statprof.display()
        
    def __del__(self):
        self.log_file.close()

    def get_config(self, configfile):
        self.config = ConfigParser.ConfigParser()
        configPath = os.path.dirname(__file__)+'/'+configfile
        self.config.read(configPath)

        self.params = {}
        self.params['write_to_db'] =            self.config.getboolean('Main', 'write_to_db')
        self.params['get_pron_from_CEDICT'] =   self.config.getboolean('Main', 'get_pron_from_CEDICT')
        self.params['write_to_pleco_db'] =      self.config.getboolean('Main', 'write_to_pleco_db')
        self.params['show_progress'] =          self.config.getboolean('Main', 'show_progress')
        self.params['approx_count_of_words'] =  self.config.getint('Main', 'approx_count_of_words')
        self.params['from_word_number'] =       self.config.getint('Main', 'from_word_number')
        self.params['to_word_number'] =         self.config.getint('Main', 'to_word_number')

        self.params['input_bkrs_file'] =        self.config.get('Input files', 'bkrs_db')
        self.params['additional_pronounces_file'] = self.config.get('Input files', 'additional_pronounces')
        self.params['char_freq_file'] =         self.config.get('Input files', 'char_freq')
        self.params['log_template'] =           self.config.get('Input files', 'log_template')

        self.params['output_pleco_database_file'] = self.config.get('Output files', 'pleco_db')
        self.params['output_database_file'] =   self.config.get('Output files', 'sqlite_db')
        self.params['log_file'] =               self.config.get('Output files', 'log_file')
        self.params['bad_words_file'] =         self.config.get('Output files', 'bad_words_html')
        self.params['bad_words_list'] =         self.config.get('Output files', 'bad_words_list')
        self.params['bad_hanzi_list'] =         self.config.get('Output files', 'bad_hanzi_list')
        self.params['frequency_file'] =         self.config.get('Output files', 'frequency')

    def log_hanzi_stat(self):

        frequency_file = open(self.params['frequency_file'], 'w', 100)
        hanzilist = []
        for key, val in self.hanzi_stat.items():
            hanzilist.append(val)

        uniquehanzi = len(hanzilist)
        allhanzi = 0
        for h in hanzilist:
            allhanzi += h['count']

        self.log('Hanzi statistic ################################################################################')
        self.log('Total hanzi:  '+str(allhanzi))
        self.log('Unique hanzi: '+str(uniquehanzi))
        self.log('Top 100 error hanzi ############################################################################')
        hanzilist.sort(key=lambda x: x['error'], reverse = True)
        i = 0
        for hanzi in hanzilist:
            i += 1
            self.log('Hanzi: '+hanzi['hanzi']+' \t Count: '+str(hanzi['count'])+'\t\tError: '+str(hanzi['error']), with_time = False)
            if i>100:
                break
        self.log('Hanzi frequency ##################################################################################')
        hanzilist.sort(key=lambda x: x['count'], reverse = True)
        i = 0
        for hanzi in hanzilist:
            frequency_file.write(hanzi['hanzi'].encode('utf-8')+'\t'+str(hanzi['count'])+'\n')
            i += 1
            if i<100:
                self.log('Hanzi #'+str(i)+': '+hanzi['hanzi']+' \t Frequency: '+str(hanzi['count']), with_time = False)
            
        frequency_file.close()

    def get_string_pron(self, ob_pron): 
        """Get list of pron: [pron1,pron2]
        pron = [(hanzi, num_pinyin, sep), ...]
        return string 
        """
        if not ob_pron:
            return ''
        list_pron = []
        for pron in ob_pron:
            str_pron = ''
            for hanzi, num_pinyin, sep in pron:
                str_pron = str_pron+num_pinyin+sep
            list_pron.append(str_pron)

        num_pron = ', '.join(list_pron)
        return num_pron.strip()

    def convert_full_pinyin(self, hanziword, pinyin):
        clean_hanzi = self.filter_hanzi(hanziword)
        pinyin = self.filter_pinyin(pinyin)

        if self.hanziword_have_comma(hanziword):
            pinyin = self.replace_comma(pinyin, rep = ' ')
            
        pinyins = pinyin.split(',')

        if len(clean_hanzi) == 0: 
            self.log('Error Hanzi word length is zero! Hanzi: '+hanziword+' clean Hanzi: '+clean_hanzi)
            self.last_error['description'] = 'NOT_CHINESE_CHARS'
            return False

        pinyins_good_results = []
        for atom_pinyin in pinyins:
            pron = self.convert_pinyin(clean_hanzi, atom_pinyin, reverse_sort = True)
            if not pron:
                pron = self.convert_pinyin(clean_hanzi, atom_pinyin, reverse_sort = False)
            if pron:
                pinyins_good_results.append(pron)
        return pinyins_good_results

    def convert_pinyin(self, clean_hanzi, pinyin, reverse_sort = True):        
        old_pinyin = pinyin
        ob_pronounce = []
        num_pinyin = ''

        for hanzi in clean_hanzi:
            all_pron_variants = self.get_all_pron_variants(hanzi)
            if re.match('^[0-9]$',hanzi):
                all_pron_variants_mixed = all_pron_variants
            else:
                all_pron_variants_mixed = self.get_with_mixed_tones(all_pron_variants, reverse_sort)
            if not all_pron_variants_mixed:
                if self.params['get_pron_from_CEDICT']:
                    self.log('cjklib getReadingForCharacter() and CEDICT() return empty list for hanzi: '+hanzi)
                else:
                    self.log('cjklib getReadingForCharacter() return empty list for hanzi: '+hanzi)
                self.last_error['description'] = 'HANZI_WITH_NO_PRON'
                try:
                    self.bad_hanzi_list.write(hanzi.encode('utf-8')+'\n')
                except:
                    pass
                return False
            not_found = True
            for pron_var in all_pron_variants_mixed: 
                if pinyin.startswith(pron_var):
                    pinyin = pinyin.replace(pron_var, '', 1)
                    if pinyin.startswith(' '): 
                        sep = ' '
                    else: 
                        sep = ''
                    pinyin = pinyin.strip()
                    if not self.have_tone_mark(pron_var) and re.match(u'^[a-zA-Zα-ωΑ-Ω]$',hanzi):
                        num_pron_var = pron_var
                    else:
                        num_pron_var = self.get_numeric_tone(pron_var)
                    ob_pronounce.append((hanzi, num_pron_var, sep))
                    num_pinyin = num_pinyin+num_pron_var 
                    not_found = False
                    break
            if not_found:   
                self.hanzi_stat[hanzi]['error'] += 1     
                matched_str = ' '.join('['+h+':'+p+']' for h,p,s in ob_pronounce)
                self.log('Not found pron for hanzi: '+hanzi+' ['+ ' '.join(s for s in all_pron_variants)+'] P1:'+old_pinyin+' P2:'+pinyin+' '+matched_str)
                self.last_error['match'] = matched_str
                self.last_error['not_match'] = hanzi+' ['+ ' '.join(s for s in all_pron_variants)+']'
                return False

        return ob_pronounce

    def get_all_pron_variants(self, hanzi):
        pron_variants = []
        try:
            pron_variants = pron_variants + self.additional_reading[hanzi]
        except KeyError:
            pass # Not in additional reading file

        try:
            pron_variants = pron_variants + self.cjk.getReadingForCharacter(hanzi, 'Pinyin')
        except:
            self.log('Error: getReadingForCharacter. Hanzi: '+hanzi)

        try:
            self.hanzi_stat[hanzi]['count'] += 1
        except KeyError:
            self.hanzi_stat[hanzi] = {'hanzi': hanzi, 'count':1, 'error':0}

        if not pron_variants:
            if self.params['get_pron_from_CEDICT']:
                pron_variants = self.get_cedict_pron_variants(hanzi)
        if not pron_variants:
            return []

        unique_pron_vars = []
        for v in pron_variants:
            if v.strip() not in unique_pron_vars:
                unique_pron_vars.append(v.strip())

        return unique_pron_vars

    def get_with_mixed_tones(self, pron_var_list, reverse_sort = True):

        all_pron_variants = pron_var_list
   
        for pron_var in pron_var_list:
            none_tone_pron = self.get_without_tone_mark(pron_var)
            alltones = self.get_all_tones(none_tone_pron)
            all_pron_variants = all_pron_variants+alltones
        for pron_var in pron_var_list:  
            none_tone_pron = self.get_without_tone_mark(pron_var)
            all_pron_variants.append(none_tone_pron)

        all_unique_pron_variants = []
        for v in all_pron_variants:
            if v not in all_unique_pron_variants:
                all_unique_pron_variants.append(v)
        all_unique_pron_variants.sort(key=len, reverse = reverse_sort)

        return all_unique_pron_variants


    def load_additional_pronounces(self):
        self.flog('Start loading additional reading database...')
        addreadfile = open(self.params['additional_pronounces_file'], mode = 'r')
        words = 0
        for line in addreadfile:
            line = line.replace('﻿','') # replace one not printable symbol
            uline = line.strip().decode('utf-8')
            charhanzilist = uline.split('\t')[0].strip().split(',')
            readings = uline.split('\t')[1].split(',')
            for charhanzi in charhanzilist:
                if charhanzi in self.additional_reading:
                    self.additional_reading[charhanzi] += readings
                else:
                    self.additional_reading[charhanzi] = readings
                words += 1
        self.flog('Additional reading database loaded. Count of hieroglyph: '+str(words))

    def load_character_frequency(self):
        self.flog('Start loading character frequency...')
        freqfile = open(self.params['char_freq_file'], mode = 'r')
        words = 0
        for line in freqfile:
            uline = (line[:-1]).strip().decode('utf-8')
            charhanzi = uline.split('\t')[0].strip()
            freq = int(uline.split('\t')[1])
            if freq <= 0:
                freq = 1
            self.hanzi_freq[charhanzi] = freq
            words += 1
        self.flog('Characters frequency loaded. Hanzi count: '+str(words))

    def get_hanzi_freq(self, hanzi):
        try:
            freq = self.hanzi_freq[hanzi]
        except KeyError:
            freq = 1 
        return freq  

    def get_word_freq(self, word): 
        freq = 0
        length = len(word)
        if not length:
            return 0
        for hanzi in word:
            freq += self.get_hanzi_freq(hanzi)
        freq = int(freq/length)
        return freq   

    def filter_hanzi(self, hanziword):
        # Unicode blocks for Chinese, Japanese and Korean:
        #{InCJK_Compatibility}: U+3300–U+33FF
        #{InCJK_Unified_Ideographs_Extension_A}: U+3400–U+4DBF 
        #{InCJK_Unified_Ideographs}: U+4E00–U+9FFF
        #{InCJK_Compatibility_Ideographs}: U+F900–U+FAFF
        #{InCJK_Compatibility_Forms}: U+FE30–U+FE4F 

        clean_word = ''
        for char in re.findall(ur'[0-9a-zA-Zα-ωΑ-Ω\u3300-\u33FF\u3400-\u4DBF\u4e00-\u9fff\uF900-\uFAFF\uFE30-\uFE4F]+', hanziword):
            clean_word = clean_word+char
        clean_word = self.replace_comma(clean_word, rep = '')
        return clean_word


    def join_nonprintable_hanzi(self, hanziword):
        hanzi_to_join = {u'鱼岁':u'鱥'}
        for hanzi in hanzi_to_join:
            hanziword = hanziword.replace(hanzi, hanzi_to_join[hanzi])
        return hanziword

    def get_trad(self, simp_word):
        tradchars = []
        for schar in simp_word:
            tchar = self.get_alternative_hanzi(self.charInfo.getTraditional(schar)[0],schar)
            tradchars += tchar
        tradword = ''.join(tradchars)
        return tradword

    def get_alternative_hanzi(self, chars, simple_char):
        alt = chars[0]
        for char in chars:
            if char != simple_char:
                alt = char
        return alt


    def replace_comma(self, hanziword, rep = ''):
        for comma in self.comma_symbols:
            hanziword = hanziword.replace(comma, rep)
        return hanziword

    def hanziword_have_comma(self, hanziword):
        for comma in self.comma_symbols:
            if comma in hanziword:
                return True
        return False

    def pinyin_have_bad_symbol(self, pinyin):
        for symb in [u'​', u'·', u'/', u'　', u'\\']:
            if symb in pinyin:
                return True
        return False

    def word_highlight_bad_sybmols(self, word):
        word = re.sub(ur'([^0-9a-zA-Z\u3300-\u33FF\u3400-\u4DBF\u4e00-\u9fff\uF900-\uFAFF\uFE30-\uFE4F ，,-]+)','<b class="red">('+r'\1'+')</b>', word)
        return word

    def pinyin_highlight_bad_sybmols(self, pinyin):
        pinyin = re.sub(ur'([^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü ,]+)','<b class="red">('+r'\1'+')</b>', pinyin)
        return pinyin

    def filter_pinyin(self, pinyin):
        pinyin = re.sub('\([^)]+\)', '', pinyin) #delete (...)
        pinyin = self.replace_comma(pinyin, ',') 
        pinyin = self.replace_tags_with_content(pinyin, ',')
        pinyin = re.sub('[;,]+', ',', pinyin)
        pinyin = re.sub('[,]+', ',', pinyin)
        pinyin = pinyin.replace(u'​', ' ') # non visible symbol!
        pinyin = pinyin.replace(u'·', ' ') 
        pinyin = pinyin.replace(u'\\', ' ') 
        #pinyin = re.sub(u'[‘　’`….‧—–/:-]+', ' ', pinyin)
        pinyin = re.sub(u'[‘　`….‧—–/:-]+', ' ', pinyin)
        pinyin = re.sub('[ ]+',' ', pinyin)
        pinyin = re.sub(',[ ,]*,',',', pinyin)
        pinyin = re.sub('[ ]*[,]+[ ]*',',', pinyin)
        pinyin = pinyin.strip(' ')
        pinyin = pinyin.strip(',')

        pinyin = pinyin.replace(u'ĕ',u'ě')
        pinyin = pinyin.replace(u'ă',u'ǎ')
        pinyin = pinyin.replace(u'ĭ',u'ǐ')
        return pinyin

    def log(self, message, with_time = True):
        message = message.encode('utf-8')
        con_time = time.strftime('%H:%M:%S')
        log_time = time.strftime('%b %d %Y %H:%M:%S')
        if not with_time:
            con_time = ''
            log_time = ''

        self.log_file.write(log_time+'  '+message+'\n')

    def flog(self, message):
        self.log(message, with_time = True)

    def show_progress(self, cur_index, max_index):
        if max_index <= 0:
            max_index = self.params['approx_count_of_words']
        if max_index < 100:
            return
        if cur_index%(int(max_index/100)) == 0:
            self.flog('Working... '+str(cur_index*100/max_index)+'%')
        
    def create_db(self):
        self.log('Create db')
        self.cursor.execute('DROP TABLE IF EXISTS dict')
        self.conn.commit()
        self.cursor.execute('CREATE TABLE dict (trad TEXT, simp TEXT, pinyin TEXT, entry TEXT, freq INTEGER);')
        self.conn.commit()

    def write_db(self, t_hanzi, s_hanzi, pinyin, translate, freq):
        self.cursor.execute('INSERT INTO dict VALUES(?,?,?,?,?)', (t_hanzi, s_hanzi, pinyin, translate, freq))     

    def create_db_index(self):
        self.log('Create db index')
        self.cursor.execute('CREATE INDEX ix_simp ON dict (simp ASC);')
        self.cursor.execute('CREATE INDEX ix_trad ON dict (trad ASC);')
        self.conn.commit()

    def remove_html_tags(self, string):
        string = re.sub(r'\[[a-zA-Z0-9/ ]+\]', ' ', string)
        string = re.sub(r'[ ]+', ' ', string)
        string = re.sub(r'^[ ]+([^ ].+?)$', r'\1', string)
        return string

    def have_pron_symbol(self, pron):
        pronsymbols = u'abcdefghijklmnopqrstuvwxyzāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü'
        pron = re.sub('\[.*?\]', ' ', pron) #delete tags
        for char in pron:
            if char in pronsymbols:
                return True
        return False

    def have_lat_letters_or_numbers(self, word):
        pronsymbols = u'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        for char in word:
            if char in pronsymbols:
                return True
        return False

    def have_tag_symbol(self, word):
        if re.findall(u'\[[a-z/]+\]', word):
            return True
        return False

    def get_all_tones(self, entity):
        alltones = []
        try:
            alltones.append(self.pinyinOp.getTonalEntity(entity,1))
            alltones.append(self.pinyinOp.getTonalEntity(entity,2))
            alltones.append(self.pinyinOp.getTonalEntity(entity,3))
            alltones.append(self.pinyinOp.getTonalEntity(entity,4))
        except:
            self.log('Error getTonalEntity() Entity: '+entity)
        return alltones

    def get_without_tone_mark(self, entity):
        null_tone_pron = self.read_fab.convert(entity, 'Pinyin', 'Pinyin', targetOptions={'toneMarkType': 'none'})
        return null_tone_pron

    def get_numeric_tone(self, entity):
        num_pron = self.read_fab.convert(entity, 'Pinyin', 'Pinyin', targetOptions={'toneMarkType': 'numbers'})
        return num_pron

    def have_tone_mark(self, pron):
        tonemarksymbols = u'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ'
        for char in pron:
            if char in tonemarksymbols:
                return True
        return False

    def have_rus_letters(self, word):
        rusletters = u'ёйцукенгшщзхъфывапролджэячсмитьбюЁЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ'
        for char in word:
            if char in rusletters:
                return True
        return False

    def replace_tags_with_content(self, string, rep = ''):
        string = re.sub('\[[a-z0-9]+\][^\[]*\[/[a-z0-9]+\]', rep, string) #delete tags level 1
        string = re.sub('\[[a-z0-9]+\][^\[]*\[/[a-z0-9]+\]', rep, string) #delete tags level 2
        string = re.sub('\[[a-z0-9]+\][^\[]*\[/[a-z0-9]+\]', rep, string) #delete tags level 3
        return string

    def replace_cp_tags_with_content(self, string, rep = ''):
        string = re.sub('\[[cp]\][^\[]*\[/[cp]\]', rep, string) #delete tags level 1
        string = re.sub('\[[cp]\][^\[]*\[/[cp]\]', rep, string) #delete tags level 1
        string = re.sub('\[[cp]\][^\[]*\[/[cp]\]', rep, string) #delete tags level 1
        return string

    def translate_have_rus(self, translate):
        tr = self.replace_cp_tags_with_content(translate)
        return self.have_rus_letters(tr)

    def have_number_symbol(self, pron):
        numsim = u'1234567890'
        for char in pron:
            if char in numsim:
                return True
        return False

    def get_cedict_pron_variants(self, hanzi):
        pron_vars = []
        cedict = CEDICT()
        for entrie in cedict.getFor(hanzi):
            pron_vars.append(entrie.Reading)
        return pron_vars

    def log_bad_word(self, word, pinyin, str_error, translate, word_index):
        self.bad_word_index += 1
        highlighted_word = self.word_highlight_bad_sybmols(word)
        highlighted_pinyin = self.pinyin_highlight_bad_sybmols(pinyin)
        if highlighted_pinyin.find('<b class="red">') != -1:
            fpinyin_sort_field = '0'
        else:
            fpinyin_sort_field = '1'

        freq = self.get_word_freq(self.filter_hanzi(self.last_error['not_match']))
        error_descr = self.errors_description[str_error]

        self.bad_words_file.write('<tr class="'+str_error+'">\n')
        self.bad_words_file.write('<td class="number">'+str(self.bad_word_index)+'#'+str(word_index)+'</td>\n')
        self.bad_words_file.write('\t<td class="error-info">'+error_descr+'</td>\n')
        self.bad_words_file.write('\t<td class="word" sorttable_customkey="'+str(len(word))+'"><a target="_blank" href="http://bkrs.info/slovo.php?ch='+word.encode('utf-8')+'">'+highlighted_word.encode('utf-8')+'</a></td>\n')
        self.bad_words_file.write('\t<td class="pinyin">'+pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="filtered-pinyin" sorttable_customkey="'+fpinyin_sort_field+'">'+highlighted_pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="match">'+self.last_error['match'].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="not_match">'+self.last_error['not_match'].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="freq" sorttable_customkey="'+str(freq)+'">'+str(freq)+'</td>\n')
        self.bad_words_file.write('\t<td class="translate" sorttable_customkey="'+str(len(translate))+'">'+self.remove_html_tags(translate)[:50].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('</tr>\n')

    def clear_last_error(self):
        self.last_error = {'description':'', 'match':'', 'not_match': ''}

    def start_bad_words_file(self):
        f = open(self.params['log_template'], 'r')
        starthtml = f.read()
        f.close()
        self.bad_words_file.write(starthtml)

    def end_bad_words_file(self):
        endhtml = "</table></body></html>"
        self.bad_words_file.write(endhtml)

##############################################################################################################
#b = BKRS2DB(configfile = 'input_files/config.ini')
#b.export()