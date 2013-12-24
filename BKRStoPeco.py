# -*- coding: utf-8 -*-
import re
import sqlite3
import time
import sys
import cjklib #http://cjklib.org/0.3/
from cjklib.reading import ReadingFactory 
from cjklib import characterlookup
from cjklib.dictionary import CEDICT


params = {
    'input_bkrs_file':        'dabkrs_131222.txt',#'small_bkrs.txt',
    'write_to_db':            True,
    'output_database_file':   'bkrs.pqb',
    'from_word_number':       0 ,
    'to_word_number':         1000, #1835721
    'log_to_console':         False,
    'log_file':               'log_file.txt',
    'bad_words_file':         'BKRS_bad_words.html',
    'show_progress':          True,
    'get_pron_from_CEDICT':   False,
}


class BKRS2Pleco(object):

    """Class to convert BKRS.info dictionary into Pleco database format"""
    def __init__(self, params):
        super(BKRS2Pleco, self).__init__()
        self.params = params

        self.PLC_NEW_LINE = '\xEE\xAA\xB1'.decode('utf-8')
        self.PLC_START_BOLD = '\xEE\xAA\xB2'.decode('utf-8')
        self.PLC_STOP_BOLD = '\xEE\xAA\xB3'.decode('utf-8')

        self.BUFFER_SIZE = 10000
        self.buffer_index = 0
        self.SKIP_WORD_INDEX = params['from_word_number']
        self.MAX_WORD_INDEX = params['to_word_number']

        self.read_fab = ReadingFactory()
        self.cjk = characterlookup.CharacterLookup('T')
        self.pinyinOp = self.read_fab.createReadingOperator('Pinyin')
        self.last_error = ''
        self.last_error_info = ''
        self.bad_word_index = 0
        

    def export(self):
        if self.params['write_to_db']:
            self.conn = sqlite3.connect(self.params['output_database_file'])
            self.cursor = self.conn.cursor()
        self.log_file = open(self.params['log_file'], 'w', 1000)
        self.bad_words_file = open(self.params['bad_words_file'], 'w', 1000)
        self.start_bad_words_file()
        

        self.log('Start of export. Input: '+self.params['input_bkrs_file']+', output: '+self.params['output_database_file'])
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
                        if word_index >= self.MAX_WORD_INDEX:
                            break
                        translate = (line[1:-1]).strip().decode('utf-8')
                        translate_with_tags = translate
                        translate = self.remove_html_tags(translate)
                        translate = self.remove_trash(translate)
                        word_info = ' line #'+str(word_index*4+1)+' word #'+str(word_index)+' word: '+word+' pinyin: '+pronounce

                        if self.have_rus_letters(pronounce):
                            if not self.have_tone_mark(pronounce):
                                self.log('Warning: pinyin have no tone mark but have russian letters'+word_info)
                                self.log_bad_word(word, pronounce, 'Есть русские буквы и нет знака тона', translate_with_tags, word_index)

                        if self.have_tone_number(pronounce):
                            pinyin_have_tone_number += 1
                            continue

                        if self.have_tag_symbol(pronounce):
                            self.log('Warning: pinyin have tag symbols '+word_info)
                            self.log_bad_word(word, pronounce, 'Есть HTML\'s теги', translate_with_tags, word_index)
                            pinyin_have_tag_symbol +=1
                            continue
                            
                        if not self.have_rus_letters(translate):
                            have_no_rus_translate += 1
                            continue

                        pronounce = self.remove_html_tags(pronounce)

                        if self.have_pron_symbol(pronounce):
                            ob_pronounce = self.convert_full_pinyin(word, pronounce)
                            pronounce_numeric_tone = self.get_string_pron(ob_pronounce)
                            if not pronounce_numeric_tone:
                                self.log('Error not found pronounce variant'+word_info)
                                bad_word_not_found_pron_variant += 1
                                if self.last_error != 'NO_PRON_VARIANTS':
                                    self.log_bad_word(word, pronounce, 'Не совпадает', translate_with_tags, word_index)               
                                continue
                        else:
                            no_pron_symbols_in_pinyin += 1
                            continue

                        if self.params['write_to_db']:
                            self.write_db(word, pronounce_numeric_tone, translate)
                            self.create_db_word_index(ob_pronounce, len(word))
                        self.clear_last_error()
                        good_words += 1



        self.log('OK..')
        self.log('Count of words:\t\t\t\t\t'+str(word_index))
        self.log('Good words:\t\t\t\t\t\t'+str(good_words)+'\t\t('+str(round(float(good_words)*100/word_index,2))+'%)')
        self.log('Have no rus translate:\t\t\t'+str(have_no_rus_translate)+'\t\t('+str(round(float(have_no_rus_translate)*100/word_index,2))+'%)')
        self.log('Not found pronounce variant:  \t'+str(bad_word_not_found_pron_variant)+'\t\t('+str(round(float(bad_word_not_found_pron_variant)*100/word_index,2))+'%)')
        self.log('Numeric pinyin have tone mark:\t'+str(num_pinyin_have_tone_mark)+'\t\t('+str(round(float(num_pinyin_have_tone_mark)*100/word_index,2))+'%)')
        self.log('Pinyin field have tone number:\t'+str(pinyin_have_tone_number)+'\t\t('+str(round(float(pinyin_have_tone_number)*100/word_index,2))+'%)')
        self.log('Pinyin pinyin have tag symbol:\t'+str(pinyin_have_tag_symbol)+'\t\t('+str(round(float(pinyin_have_tag_symbol)*100/word_index,2))+'%)')
        self.log('Pinyin have no pron symbols:  \t'+str(no_pron_symbols_in_pinyin)+'\t\t('+str(round(float(no_pron_symbols_in_pinyin)*100/word_index,2))+'%)')

        if self.params['write_to_db']:
            self.create_db_index()
            self.conn.commit()
            self.conn.close()

        self.dic.close()
        self.end_time = time.time()
        self.log('End of export. Total time: '+str(round(self.end_time - self.start_time ,2))+' sec')
        self.log_file.close()
        self.end_bad_words_file()
        self.bad_words_file.close()

    def create_db(self):
        str_db_created = str(int(time.time()))

        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_properties')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_entries')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_hz_1')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_hz_2')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_hz_3')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_hz_4')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_py_1')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_py_2')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_py_3')
        self.cursor.execute('DROP TABLE IF EXISTS pleco_dict_posdex_py_4')
        self.cursor.execute('CREATE TABLE pleco_dict_properties ("propset" INTEGER, "propid" TEXT, "propvalue" TEXT, "propisstring" INTEGER, UNIQUE ("propset", "propid") )')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FormatString","Pleco SQL Dictionary Database",1)')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FormatVersion","8",0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FileGenerator","Pleco Engine 2.0",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FilePlatform","Android",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FileCreated",?,0);',(str_db_created,))
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FileCreator","16796996",0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"FileID","-1530540358",0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictMenuName","BKRS Ch-Ru",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictShortName","BKRS Ch-Ru",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictName","Pleco BKRS Chinese-Russian Dictionary",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictLang","Chinese",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"TransLang","English",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"EditLock",NULL,0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"SortMethod",NULL,0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"NoSortKey",NULL,0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictIconName","BKR",1);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictIconFillColor","39372",0);')
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"DictIconTextColor","16777215",0);')
        self.cursor.execute('CREATE TABLE pleco_dict_entries ("uid" INTEGER PRIMARY KEY AUTOINCREMENT, "created" INTEGER, "modified" INTEGER, "length" INTEGER, "word" TEXT COLLATE NOCASE, "altword" TEXT COLLATE NOCASE, "pron" TEXT COLLATE NOCASE, "defn" TEXT, "sortkey" TEXT UNIQUE);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_hz_1" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER, "length" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_hz_2" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_hz_3" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_hz_4" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_py_1" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER, "length" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_py_2" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_py_3" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.cursor.execute('CREATE TABLE "pleco_dict_posdex_py_4" ("syllable" TEXT COLLATE NOCASE, "uid" INTEGER);')
        self.conn.commit()


    def write_db(self, word, pronounce, translate):
        ctime = str(int(time.time()))
        wordlen = len(word)
        translate = translate
        try:
            self.cursor.execute('INSERT INTO pleco_dict_entries VALUES (NULL,?,?,?,?,NULL,?,?,?)', (ctime, ctime, wordlen, word, pronounce, translate, pronounce+word))
            self.db_last_insert_id = self.cursor.lastrowid
        except:
            self.log('DB Error: '+str(sys.exc_info()[0])+' word: '+word)

        self.buffer_index += 1
        if self.buffer_index > self.BUFFER_SIZE:
            self.buffer_index = 0
            self.conn.commit()

    def create_db_word_index(self, ob_pron, wordlen):
        pronounciations = []
        list_pron = []
        for pron in ob_pron:
            i = 0
            for hanzi, num_pinyin in pron:
                i += 1
                if i == 1:
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_hz_1 VALUES(?,?,?)',(hanzi, self.db_last_insert_id, wordlen))
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_py_1 VALUES(?,?,?)',(num_pinyin, self.db_last_insert_id, wordlen))
                if i == 2:
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_hz_2 VALUES(?,?)',(hanzi, self.db_last_insert_id))
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_py_2 VALUES(?,?)',(num_pinyin, self.db_last_insert_id))
                if i == 3:
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_hz_3 VALUES(?,?)',(hanzi, self.db_last_insert_id))
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_py_3 VALUES(?,?)',(num_pinyin, self.db_last_insert_id))
                if i == 4:
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_hz_4 VALUES(?,?)',(hanzi, self.db_last_insert_id))
                    self.cursor.execute('INSERT INTO pleco_dict_posdex_py_4 VALUES(?,?)',(num_pinyin, self.db_last_insert_id))


    def create_db_index(self):
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_1_syllable_uid_length ON pleco_dict_posdex_hz_1 ("syllable", "uid", "length");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_1_uid ON pleco_dict_posdex_hz_1 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_2_syllable_uid ON pleco_dict_posdex_hz_2 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_2_uid ON pleco_dict_posdex_hz_2 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_3_syllable_uid ON pleco_dict_posdex_hz_3 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_3_uid ON pleco_dict_posdex_hz_3 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_4_syllable_uid ON pleco_dict_posdex_hz_4 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_hz_4_uid ON pleco_dict_posdex_hz_4 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_1_syllable_uid_length ON pleco_dict_posdex_py_1 ("syllable", "uid", "length");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_1_uid ON pleco_dict_posdex_py_1 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_2_syllable_uid ON pleco_dict_posdex_py_2 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_2_uid ON pleco_dict_posdex_py_2 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_3_syllable_uid ON pleco_dict_posdex_py_3 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_3_uid ON pleco_dict_posdex_py_3 (uid);')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_4_syllable_uid ON pleco_dict_posdex_py_4 ("syllable", "uid");')
        self.cursor.execute('CREATE INDEX idx_pleco_dict_posdex_py_4_uid ON pleco_dict_posdex_py_4 (uid);')
        self.conn.commit()
                

    def get_string_pron(self, ob_pron): 
        """Get list of pron: [pron1,pron2]
        pron = [(hanzi, num_pinyin), ...]
        return string 
        """
        if not ob_pron:
            return ''
        pronounciations = []
        list_pron = []
        for pron in ob_pron:
            str_pron = ''
            for hanzi, num_pinyin in pron:
                str_pron = str_pron+num_pinyin
            list_pron.append(str_pron)
        return ', '.join(list_pron)

    def convert_full_pinyin(self, hanziword, pinyin):
        clean_hanzi = self.filter_hanzi(hanziword)
        pinyin = self.filter_pinyin(pinyin)

        if self.hanziword_have_comma(hanziword):
            pinyin = pinyin.replace(',',' ')
            
        pinyins = pinyin.split(',')

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
            all_pron_variants = self.get_all_pron_variants(clean_hanzi, mixtones = False)
            if not all_pron_variants:
                self.log('cjklib 2 getReadingForCharacter() and CEDICT() return empty list for hanzi: '+clean_hanzi)
                self.last_error = 'NO_PRON_VARIANTS'
                return False
            all_num_pron_variants = []
            for v in all_pron_variants:
                all_num_pron_variants.append([(clean_hanzi, self.get_num_pron(v))])

            return all_num_pron_variants

        for hanzi in clean_hanzi:
            all_pron_variants = self.get_all_pron_variants(hanzi)
            if not all_pron_variants:
                self.log('cjklib getReadingForCharacter() and CEDICT() return empty list for hanzi: '+hanzi)
                self.last_error = 'NO_PRON_VARIANTS'
                return False
            not_found = True
            for pron_var in all_pron_variants: 
                if pinyin.startswith(pron_var):
                    pinyin = pinyin.replace(pron_var, '', 1).strip()
                    num_pron_var = self.get_num_pron(pron_var)
                    ob_pronounce.append((hanzi,num_pron_var))
                    num_pinyin = num_pinyin+num_pron_var 
                    not_found = False
                    break
            if not_found:        
                pstr = ' '.join('['+h+':'+p+']' for h,p in ob_pronounce)
                self.log('Not found pron for hanzi: '+hanzi+' ['+ ' '.join(s for s in all_pron_variants)+'] P1:'+old_pinyin+' P2:'+pinyin+' '+pstr)
                self.last_error_info = pstr+' '+hanzi+' ['+ ' '.join(s for s in all_pron_variants)+']'
                return False

        return ob_pronounce

    def get_all_pron_variants(self, hanzi, mixtones = True):
        try:
            pron_variants = self.cjk.getReadingForCharacter(hanzi, 'Pinyin')
        except:
            self.log('Error: getReadingForCharacter. Hanzi: '+hanzi)
            return False 

        if not pron_variants:
            if self.params['get_pron_from_CEDICT']:
                pron_variants = self.get_cedict_pron_variants(hanzi)

        if not pron_variants:
            return False

        all_pron_variants = pron_variants
        if mixtones:
            for pron_var in pron_variants:
                none_tone_pron = self.get_without_tone(pron_var)
                alltones = self.get_all_tones(none_tone_pron)
                all_pron_variants = all_pron_variants+alltones
            for pron_var in pron_variants:  
                none_tone_pron = self.get_without_tone(pron_var)
                all_pron_variants.append(none_tone_pron)

            all_unique_pron_variants = []
            for v in all_pron_variants:
                if v not in all_unique_pron_variants:
                    all_unique_pron_variants.append(v)
            all_unique_pron_variants.sort(key=len, reverse=True)
        else:
            all_unique_pron_variants = all_pron_variants
        return all_unique_pron_variants
        

    def filter_hanzi(self, hanziword):
        clean_word = ''
        for char in re.findall(ur'[\u4e00-\u9fff]+', hanziword):
            clean_word = clean_word+char
        clean_word = clean_word.replace(u'﹐', '')
        clean_word = clean_word.replace(u'，', '')
        return clean_word

    def hanziword_have_comma(self, hanziword):
        if u'﹐' in hanziword:
            return True
        if u'，' in hanziword: 
            return True
        return False

    def filter_pinyin(self, pinyin, for_human_detect = False):
        pinyin = re.sub(r'[;,]+', ',', pinyin)
        pinyin = re.sub(r'[,]+', ',', pinyin)
        pinyin = re.sub(r'[ ]+', ' ', pinyin)
        if for_human_detect:
            pinyin = re.sub(ur'([^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü,])','<b class="red">'+r'\1'+'</b>', pinyin)
        else:
            pinyin = re.sub(ur'[^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü,]',' ', pinyin)
        pinyin = re.sub(ur'[ ]*,[ ]*',',', pinyin)
        return pinyin.strip()

    def log(self, message):
        message = message.encode('utf-8')
        con_time = time.strftime('%H:%M:%S')
        log_time = time.strftime('%b %d %Y %H:%M:%S')
        if self.params['log_to_console']:
            try:
                print con_time+'    '+message
            except:
                print con_time+'    '+'Log to console error'
       
        self.log_file.write(log_time+'  '+message+'\n')

    def show_progress(self, cur_index, max_index):
        if cur_index%(int(max_index/100)) == 0:
            self.log('Working... '+str(cur_index*100/max_index)+'%')
        

    def remove_html_tags(self, string, use_pleco_features = True):
        if use_pleco_features:
            new_line = self.PLC_NEW_LINE
            start_bold = self.PLC_START_BOLD
            stop_bold = self.PLC_STOP_BOLD
        else:
            new_line = ' \n'
            start_bold = ' '
            stop_bold = ' '
        string = re.sub('\[m[1-9]\]\[\*\]\[ex\]', new_line, string)
        string = re.sub('\[m1\]', ' ', string)
        string = re.sub('\[ex\]', new_line, string)
        string = re.sub('\[m2\]', new_line*2, string)
        string = re.sub('\[m[3-9]\]', new_line, string)
        string = re.sub('\[.*?\]', ' ', string)
        string = re.sub(new_line+r'([0-9]+\))', new_line+start_bold+r'\1'+stop_bold, string)
        return string

    def remove_trash(self, word):
        word = word.replace('\ ',' ')
        word = word.replace('*',' ')
        word = re.sub(r'[ ]+', ' ', word)
        word = re.sub(r'[ ]+'+self.PLC_NEW_LINE, self.PLC_NEW_LINE, word)
        word = re.sub(self.PLC_NEW_LINE+r'[ ]+', self.PLC_NEW_LINE, word)
        return word

    def have_html_tags(self, string):
        if re.search('\[.*?\]', string):
            return True
        else:
            return False


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

    def is_trash_symbol(self, symbol):
        trash = u' …‘’`-.,;_()?'
        if symbol in trash:
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

    def only_pron_symbols_with_trash(self, pron):
        pronsymbols = u'ABCDEFGHIJKLMNUOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz …‘’`-.,;āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü_()'
        for char in pron:
            if char not in pronsymbols:
                return False
        return True

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
        self.bad_words_file.write('<tr>\n')
        self.bad_words_file.write('<td class="number"> #'+str(self.bad_word_index)+' #'+str(word_index)+' </td>\n')
        self.bad_words_file.write('\t<td class="error-info">'+str_error+'</td>\n')
        self.bad_words_file.write('\t<td class="word"><a target="_blank" href="http://bkrs.info/slovo.php?ch='+word.encode('utf-8')+'">'+word.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="pinyin">'+pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="filtered-pinyin">'+filtered_pinyin.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="match">'+self.last_error_info.encode('utf-8')+'</td>\n')
        self.bad_words_file.write('\t<td class="translate">'+self.remove_html_tags(translate, use_pleco_features = False)[:50].encode('utf-8')+'</td>\n')
        self.bad_words_file.write('</tr>\n')


    def clear_last_error(self):
        self.last_error = ''
        self.last_error_info = ''

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
        .translate{width:25%; word-break: break-all;}
        td{border: 1px solid #CCC; padding: 4px 10px;}
    </style>
</head>
<body>
<p class="title"> BKRS pinyin errors</p>
<table class="etable" style="margin:0 auto; border-collapse: collapse; border-spacing: 0;" cellpadding="0" cellspacing="0">
        """
        self.bad_words_file.write(starthtml)

    def end_bad_words_file(self):
        endhtml = """
</table>
</body>
        """
        self.bad_words_file.write(endhtml)
##############################################################################################################

bkrs = BKRS2Pleco(params)
bkrs.export()
