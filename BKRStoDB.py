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

params = {
    'log_to_console':         False,
    'input_bkrs_file':        'input_files/dabkrs_140523.txt', #http://bkrs.info/p47  --> 大БКРС vXXXXXXXXX/  http://bkrs.info/downloads/daily/dabkrs_xxxxxx.gz
    'unihan_file':            'input_files/Unihan_Readings', #ftp://ftp.unicode.org/Public/UNIDATA/Unihan.zip
    'add_readings_file':      'input_files/Additional_Readings',
    'char_freq_file':         'input_files/char_frequency.txt',
    'write_to_db':            True,
    'output_database_file':   'output_files/bkrs.db',

    # Pleco settings 
    'write_to_pleco_db':      True,
    'output_pleco_database_file':'output_files/bkrs.pqb',
    
    # Limit count of word 
    'from_word_number':       0,
    'to_word_number':         10000,

    'log_file':               'output_files/log_file.txt',
    'bad_words_file':         'output_files/bkrs_bad_words.html',
    'bad_words_list':         'output_files/bkrs_bad_words_list.txt',
    'show_progress':          True,
    'get_pron_from_CEDICT':   True,
    'approx_count_of_words':  2500000, #1835721
}


class BKRS2DB(object):

    """Class to convert BKRS.info dictionary into Pleco database format"""
    def __init__(self, params):
        super(BKRS2DB, self).__init__()
        self.params = params

        self.BUFFER_SIZE = 10000
        self.buffer_index = 0
        self.SKIP_WORD_INDEX = params['from_word_number']
        self.MAX_WORD_INDEX = params['to_word_number']

        self.read_fab = ReadingFactory()
        self.cjk = characterlookup.CharacterLookup('T')
        self.pinyinOp = self.read_fab.createReadingOperator('Pinyin')
        self.charInfo =  cjknife.CharacterInfo()
        self.last_error = {'description':'', 'match':'', 'not_match': ''}
        self.bad_word_index = 0
        self.unihan_reading = {}
        self.additional_reading = {}
        self.hanzi_stat = {}
        self.hanzi_freq = {}

        self.log_file = open(self.params['log_file'], 'w', 1000)

        if self.params['write_to_pleco_db']:
            self.pleco = Pleco(self.params['output_pleco_database_file'], self)
        
    def export(self):

        if self.params['write_to_db']:
            self.conn = sqlite3.connect(self.params['output_database_file'])
            self.cursor = self.conn.cursor()
        
        self.bad_words_file = open(self.params['bad_words_file'], 'w', 1000)
        self.bad_words_list = open(self.params['bad_words_list'], 'w', 100)

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
        pinyin_have_tone_number = 0
        self.ambiguous_decomposition = 0
        pinyin_have_tag_symbol = 0
        num_pinyin_have_tone_mark = 0
        no_pron_symbols_in_pinyin = 0

        self.load_character_frequency()

        if self.params['unihan_file']:
            self.load_readings_from_unihan()

        if self.params['add_readings_file']:
            self.load_additional_readings()

        for line in self.dic:
            if line == '\n':
                line_type = 'word'
            else:
                if not line.startswith('#'):
                    if line_type == 'word':
                        word_index = word_index+1
                        if self.params['show_progress']:
                            self.show_progress(word_index, self.MAX_WORD_INDEX)
                        word = (line[:-1]).strip().decode('utf-8')
                        line_type = 'pronounce'
                    elif line_type == 'pronounce':
                        pronounce = (line[1:-1]).strip().decode('utf-8')
                        line_type = 'translate'
                    elif line_type == 'translate':
                        if word_index <= self.SKIP_WORD_INDEX:
                            continue
                        if self.MAX_WORD_INDEX > 0:
                            if word_index >= self.MAX_WORD_INDEX:
                                break
                    
                        translate = (line[1:-1]).strip().decode('utf-8')
                        translate_with_tags = translate
                        translate_pleco = self.pleco.remove_html_tags(translate)

                        #if len(translate)<4000:
                        #    continue
                        #if len(word)<10:
                        #    continue
                        
                        word_info = ' line #'+str(word_index*4+1)+' word #'+str(word_index)+' word: '+word+' pinyin: '+pronounce

                        if self.have_rus_letters(pronounce):
                            if not self.have_tone_mark(pronounce):
                                self.log('Warning: pinyin have no tone mark but have russian letters'+word_info)
                                self.log_bad_word(word, pronounce, 'Есть русские буквы и нет знака тона', translate_with_tags, word_index)
                                self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                                continue

                        if self.have_tone_number(pronounce):
                            pinyin_have_tone_number += 1
                            self.log('Pinyin have tone number '+word_info)
                            self.log_bad_word(word, pronounce, 'В пиньине цифры', translate_with_tags, word_index)
                            self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                            continue

                        if self.have_tag_symbol(pronounce):
                            self.log('Warning: pinyin have tag symbols '+word_info)
                            self.log_bad_word(word, pronounce, 'В пиньине теги', translate_with_tags, word_index)
                            self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')
                            pinyin_have_tag_symbol +=1
                            continue
                            
                        if not self.have_rus_letters(translate_pleco):
                            have_no_rus_translate += 1
                            continue

                        pronounce = self.remove_html_tags(pronounce)

                        if self.have_pron_symbol(pronounce):
                            ob_pronounce = self.convert_full_pinyin(word, pronounce)
                            pronounce_numeric_tone = self.get_string_pron(ob_pronounce)
                            pronounce_numeric_tone_sep = self.get_string_pron(ob_pronounce, True)
                            if not pronounce_numeric_tone:
                                self.log('Error not found pronounce variant'+word_info)
                                bad_word_not_found_pron_variant += 1
                                if self.last_error['description'] != 'NOT_MATCH':
                                    self.log_bad_word(word, pronounce, 'Не совпадает', translate_with_tags, word_index)
                                    self.bad_words_list.write(word.encode('utf-8')+'\t'+pronounce.encode('utf-8')+'\n')              
                                continue
                        else:
                            no_pron_symbols_in_pinyin += 1
                            continue

                        if self.params['write_to_pleco_db']:
                            self.pleco.write_db(word, pronounce_numeric_tone, translate_pleco)
                            self.pleco.create_db_word_index(ob_pronounce, len(word))

                        if self.params['write_to_db']:
                            trad_word = self.get_trad(word)
                            freq = self.get_word_freq(word)
                            self.write_db(trad_word, word, pronounce_numeric_tone_sep, translate, freq)
                            
                        self.clear_last_error()
                        good_words += 1


        self.log('OK.. ###################################################################################')
        self.log('Count of words:\t\t\t\t\t'+str(word_index))
        self.log('Good words:\t\t\t\t\t\t'+str(good_words)+'\t\t('+str(round(float(good_words)*100/word_index,2))+'%)')
        self.log('Have no rus translate:\t\t\t'+str(have_no_rus_translate)+'\t\t('+str(round(float(have_no_rus_translate)*100/word_index,2))+'%)')
        self.log('Not found pronounce variant:  \t'+str(bad_word_not_found_pron_variant)+'\t\t('+str(round(float(bad_word_not_found_pron_variant)*100/word_index,2))+'%)')
        self.log('Numeric pinyin have tone mark:\t'+str(num_pinyin_have_tone_mark)+'\t\t('+str(round(float(num_pinyin_have_tone_mark)*100/word_index,2))+'%)')
        self.log('Pinyin field have tone number:\t'+str(pinyin_have_tone_number)+'\t\t('+str(round(float(pinyin_have_tone_number)*100/word_index,2))+'%)')
        self.log('Pinyin pinyin have tag symbol:\t'+str(pinyin_have_tag_symbol)+'\t\t('+str(round(float(pinyin_have_tag_symbol)*100/word_index,2))+'%)')
        self.log('Pinyin have no pron symbols:  \t'+str(no_pron_symbols_in_pinyin)+'\t\t('+str(round(float(no_pron_symbols_in_pinyin)*100/word_index,2))+'%)')
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
        self.log('End of export. Total time: '+str(round(self.end_time - self.start_time ,2))+' sec')
        
        self.end_bad_words_file()
        self.bad_words_list.close()
        self.bad_words_file.close()

    def __del__(self):

        self.log_file.close()

    def log_hanzi_stat(self):

        log_to_console = self.params['log_to_console']
        self.params['log_to_console'] = False

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
            i += 1
            self.log('Hanzi #'+str(i)+': '+hanzi['hanzi']+' \t Frequency: '+str(hanzi['count']), with_time = False)

        self.params['log_to_console'] = log_to_console

    def get_string_pron(self, ob_pron, separate = False): 
        """Get list of pron: [pron1,pron2]
        pron = [(hanzi, num_pinyin), ...]
        return string 
        """
        delim = ''
        if separate:
            delim = ' '

        if not ob_pron:
            return ''
        pronounciations = []
        list_pron = []
        for pron in ob_pron:
            str_pron = ''
            for hanzi, num_pinyin in pron:
                if str_pron:
                    str_pron = str_pron+delim+num_pinyin
                else:
                    str_pron = num_pinyin
            list_pron.append(str_pron)

        num_pron = ', '.join(list_pron)
        return num_pron.strip()

    def convert_full_pinyin(self, hanziword, pinyin):
        clean_hanzi = self.filter_hanzi(hanziword)
        pinyin = self.filter_pinyin(pinyin)

        if self.hanziword_have_comma(hanziword):
            pinyin = pinyin.replace(',',' ')
            
        pinyins = pinyin.split(',')

        if len(clean_hanzi) == 0: 
            self.log('Error Hanzi word length is zero! Hanzi: '+hanziword+' clean Hanzi: '+clean_hanzi)
            self.last_error['description'] = 'NOT_CHINESE_CHARS'
            return False

        if len(clean_hanzi) == 1:
            return self.convert_pinyin(clean_hanzi, pinyin, single_hanzi = True)
        if len(pinyins) > 1:
            self.log('Multipronounce in pinyin: '+pinyin+' word: '+clean_hanzi)

        pinyins_good_results = []
        for atom_pinyin in pinyins:
            pron = self.convert_pinyin(clean_hanzi, atom_pinyin)
            if pron:
                pinyins_good_results.append(pron)
        return pinyins_good_results

    def convert_pinyin(self, clean_hanzi, pinyin, single_hanzi = False):        
        old_pinyin = pinyin
        ob_pronounce = []
        num_pinyin = ''

        if single_hanzi:
            all_pron_variants = self.get_all_pron_variants(clean_hanzi)
            if not all_pron_variants:
                self.log('cjklib 2 getReadingForCharacter() and CEDICT() return empty list for hanzi: '+clean_hanzi)
                self.last_error['description'] = 'NOT_MATCH'
                return False
            all_num_pron_variants = []
            for v in all_pron_variants:
                all_num_pron_variants.append([(clean_hanzi, self.get_num_pron(v))])

            return all_num_pron_variants

        for hanzi in clean_hanzi:
            all_pron_variants = self.get_all_pron_variants(hanzi)
            all_pron_variants_mixed = self.get_with_mixed_tones(all_pron_variants, hanzi)
            if not all_pron_variants_mixed:
                if self.params['get_pron_from_CEDICT']:
                    self.log('cjklib getReadingForCharacter() and CEDICT() return empty list for hanzi: '+hanzi)
                else:
                    self.log('cjklib getReadingForCharacter() return empty list for hanzi: '+hanzi)
                self.last_error['description'] = 'NOT_MATCH'
                return False
            not_found = True
            for pron_var in all_pron_variants_mixed: 
                if pinyin.startswith(pron_var):
                    pinyin = pinyin.replace(pron_var, '', 1).strip()
                    num_pron_var = self.get_num_pron(pron_var)
                    ob_pronounce.append((hanzi,num_pron_var))
                    num_pinyin = num_pinyin+num_pron_var 
                    not_found = False
                    break
            if not_found:   
                self.hanzi_stat[hanzi]['error'] += 1     
                matched_str = ' '.join('['+h+':'+p+']' for h,p in ob_pronounce)
                self.log('Not found pron for hanzi: '+hanzi+' ['+ ' '.join(s for s in all_pron_variants)+'] P1:'+old_pinyin+' P2:'+pinyin+' '+matched_str)
                self.last_error['match'] = matched_str
                self.last_error['not_match'] = hanzi+' ['+ ' '.join(s for s in all_pron_variants)+']'
                return False

        return ob_pronounce

    def get_all_pron_variants(self, hanzi, mixtones = True):
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
            pron_variants = pron_variants + self.unihan_reading[hanzi]
        except KeyError:
            pass # Not in UNIHAN databese

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

    def get_with_mixed_tones(self, pron_var_list, hanzi):
        not_reverse_list = [u'亲']

        if hanzi in not_reverse_list:
            reverse = False
        else:
            reverse = True

        all_pron_variants = pron_var_list
   
        for pron_var in pron_var_list:
            none_tone_pron = self.get_without_tone(pron_var)
            alltones = self.get_all_tones(none_tone_pron)
            all_pron_variants = all_pron_variants+alltones
        for pron_var in pron_var_list:  
            none_tone_pron = self.get_without_tone(pron_var)
            all_pron_variants.append(none_tone_pron)

        all_unique_pron_variants = []
        for v in all_pron_variants:
            if v not in all_unique_pron_variants:
                all_unique_pron_variants.append(v)
        all_unique_pron_variants.sort(key=len, reverse = reverse)

        return all_unique_pron_variants

    def load_readings_from_unihan(self):
        self.log('Start loading UNIHAN reading database...')
        unihanfile = open(self.params['unihan_file'], mode = 'r')
        words = 0
        for line in unihanfile:
            uline = line.decode('utf-8')
            if uline.startswith('#'):
                continue
            if not uline.startswith('U+'):
                continue
            codepoint = int(uline.split('\t')[0].replace('U+',''), 16)
            fieldname = uline.split('\t')[1]
            fieldvalue = uline.split('\t')[2]
            if fieldname == 'kHanyuPinyin':
                charhanzi = cjklib.util.fromCodepoint(codepoint)
                readings = fieldvalue.split(':')[1].split(',')
                self.unihan_reading[charhanzi] = readings
                words += 1
        self.log('UNIHAN reading database loaded. Count of hieroglyph: '+str(words))

    def load_additional_readings(self):
        self.log('Start loading additional reading database...')
        addreadfile = open(self.params['add_readings_file'], mode = 'r')
        words = 0
        for line in addreadfile:
            uline = (line[:-1]).strip().decode('utf-8')
         
            charhanzi = uline.split('\t')[0].strip()
            readings = uline.split('\t')[1].split(',')
        
          
            self.additional_reading[charhanzi] = readings
            words += 1
        self.log('Additional reading database loaded. Count of hieroglyph: '+str(words))

    def load_character_frequency(self):
        self.log('Start loading character frequency...')
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
        self.log('Characters frequency loaded. Hanzi count: '+str(words))
    def get_hanzi_freq(self, hanzi):
        try:
            freq = self.hanzi_freq[hanzi]
        except KeyError:
            freq = 1 
        return freq  

    def get_word_freq(self, word): 
        freq = 0
        for hanzi in word:
            freq += self.get_hanzi_freq(hanzi)
        freq = int(freq/len(word))
        return freq     

    def filter_hanzi(self, hanziword):
        # Unicode blocks for Chinese, Japanese and Korean:
        #{InCJK_Compatibility}: U+3300–U+33FF
        #{InCJK_Unified_Ideographs_Extension_A}: U+3400–U+4DBF 
        #{InCJK_Unified_Ideographs}: U+4E00–U+9FFF
        #{InCJK_Compatibility_Ideographs}: U+F900–U+FAFF
        #{InCJK_Compatibility_Forms}: U+FE30–U+FE4F 

        clean_word = ''
        for char in re.findall(ur'[\u3300-\u33FF\u3400-\u4DBF\u4e00-\u9fff\uF900-\uFAFF\uFE30-\uFE4F]+', hanziword):
            clean_word = clean_word+char
        clean_word = clean_word.replace(u'﹐', '')
        clean_word = clean_word.replace(u'，', '')
        return clean_word

    def get_trad(self, simp_word):
        tradlist = self.charInfo.getTraditional(simp_word)
        tradchars = []
        for char in tradlist:
            tradchars += char
        tradword = ''.join(tradchars)
        return tradword

    def hanziword_have_comma(self, hanziword):
        if u'﹐' in hanziword:
            return True
        if u'，' in hanziword: 
            return True
        return False

    def filter_pinyin(self, pinyin, for_human_detect = False):
        pinyin = re.sub(r'[;,]+', ',', pinyin)
        pinyin = re.sub(r'[,]+', ',', pinyin)
        pinyin = re.sub(r'[‘’`-]+', ' ', pinyin)
        pinyin = re.sub(r'[ ]+', ' ', pinyin)
        pinyin = re.sub(r'\([^)]+\)', '', pinyin)


        pinyin = pinyin.replace(u'ĕ',u'ě')
        pinyin = pinyin.replace(u'ă',u'ǎ')
        pinyin = pinyin.replace(u'ĭ',u'ǐ')

        if for_human_detect:
            pinyin = re.sub(ur'([^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü ,])','<b class="red">'+r'\1'+'</b>', pinyin)
        else:
            pinyin =  re.sub(ur'[^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü ,]',' ', pinyin)
        pinyin = re.sub(ur'[ ]*,[ ]*',',', pinyin)
        return pinyin.strip()

    def log(self, message, with_time = True):
        message = message.encode('utf-8')
        con_time = time.strftime('%H:%M:%S')
        log_time = time.strftime('%b %d %Y %H:%M:%S')
        if not with_time:
            con_time = ''
            log_time = ''

        if self.params['log_to_console']:
            print con_time+'    '+message
        self.log_file.write(log_time+'  '+message+'\n')

    def show_progress(self, cur_index, max_index):
        if max_index <= 0:
            max_index = self.params['approx_count_of_words']
        if max_index < 100:
            return
        if cur_index%(int(max_index/100)) == 0:
            self.log('Working... '+str(cur_index*100/max_index)+'%')
        


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
        # string = re.sub('\[m[1-9]\]\[\*\]\[ex\]', ' ', string)
        # string = re.sub('\[m1\]', ' ', string)
        # string = re.sub('\[ex\]', ' ', string)
        # string = re.sub('\[m2\]', ' ', string)
        # string = re.sub('\[m[3-9]\]', ' ', string)
        # string = re.sub('\[[a-zA-Z/]*?\]', ' ', string)
        return string

    def have_pron_symbol(self, pron):
        pronsymbols = u'abcdefghijklmnopqrstuvwxyzāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü'
        pron = re.sub('\[.*?\]', ' ', pron)
        for char in pron:
            if char in pronsymbols:
                return True
        return False

    def have_tag_symbol(self, word):
        tagsymbols = ['[m]','[m2]','[m3]','[m4]','[b]']
        for tag in tagsymbols:
            if word.find(tag)!=-1:
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

    def get_without_tone(self, entity):
        null_tone_pron = self.read_fab.convert(entity, 'Pinyin', 'Pinyin', targetOptions={'toneMarkType': 'none'})
        return null_tone_pron

    def get_num_pron(self, entity):
        num_pron = self.read_fab.convert(entity, 'Pinyin', 'Pinyin', targetOptions={'toneMarkType': 'numbers'})
        return num_pron

    def only_pron_symbols(self, pron):
        pronsymbols = u'abcdefghijklmnopqrstuvwxyzāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü'
        for char in pron:
            if char not in pronsymbols:
                return False
        return True

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

    def have_tone_number(self, pron):
        numsim = u'1234'
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

    def is_ref(self, word):
        REF_SIG = u'см.'
        if word.find(REF_SIG)!=-1:
            trans = word.replace(REF_SIG,'')
            if not have_rus_letters(trans):
                return True
        return False

    def log_bad_word(self, word, pinyin, str_error, translate, word_index):

        self.bad_word_index += 1
        filtered_pinyin = self.filter_pinyin(pinyin, for_human_detect = True)
        if filtered_pinyin.find('<b class="red">') != -1:
            fpinyin_sort_field = '0'
        else:
            fpinyin_sort_field = '1'

        self.bad_words_file.write('<tr>\n')
        self.bad_words_file.write('<td class="number">'+str(self.bad_word_index)+'#'+str(word_index)+'</td>\n')
        self.bad_words_file.write('\t<td class="error-info">'+str_error+'</td>\n')
        self.bad_words_file.write('\t<td class="word"><a target="_blank" href="http://bkrs.info/slovo.php?ch='+word.encode('utf-8')+'">'+word.encode('utf-8')+'</a></td>\n')
        self.bad_words_file.write('\t<td class="pinyin">'+pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="filtered-pinyin" sorttable_customkey="'+fpinyin_sort_field+'">'+filtered_pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="match">'+self.last_error['match'].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="not_match">'+self.last_error['not_match'].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="translate">'+self.remove_html_tags(translate)[:50].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('</tr>\n')


    def clear_last_error(self):
        self.last_error = {'description':'', 'match':'', 'not_match': ''}

    def start_bad_words_file(self):
        starthtml = """<html>
<head> 
    <meta charset="utf-8"/>
    <title>BKRS pinyin errors</title>
    <style>
        .title{font-size: 24px;}
        .etable{border: 1px solid #CCCCCC; width: 99%;}
        .red{color: #FF0000;}
        .error-info{font-size: 12px; width: 70px;}
        .word{}
        .pinyin{}
        .filtered-pinyin{}
        .match{}
        .translate{width:25%;}
        td, th{border: 1px solid #CCC; padding: 4px 10px;}

        /* Sortable tables */
        table.sortable thead {
        background-color:#eee;
        color:#666666;
        font-weight: bold;
        cursor: default;
        }
    </style>
    <script src="sorttable.js"></script>
</head>
<body>
<p class="title"> BKRS pinyin errors</p>
<table class="etable sortable" style="margin:0 auto; border-collapse: collapse; border-spacing: 0;" cellpadding="0" cellspacing="0">
<tr>
    <th class="sorttable_numeric">Number</th>
    <th>Error</th>
    <th>Hanzi</th>
    <th>Pinyin</th>
    <th>Corrected pinyin</th>
    <th>Pinyin match</th>
    <th>Pinyin Not match</th>
    <th>Translate</th>
</tr>
        """
        self.bad_words_file.write(starthtml)

    def end_bad_words_file(self):
        endhtml = """
</table>
</body>
        """
        self.bad_words_file.write(endhtml)



##############################################################################################################

bkrs = BKRS2DB(params)
bkrs.export()

