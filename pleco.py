# -*- coding: utf-8 -*-
import re
import sqlite3
import time
import sys

class Pleco(object):
    def __init__(self, output_db_file, parent):
        super(Pleco, self).__init__()

        self.parent = parent
        self.conn = sqlite3.connect(output_db_file)
        self.cursor = self.conn.cursor()

        self.create_db()
        self.db_last_insert_id = 0
        self.BUFFER_SIZE = 10000
        self.buffer_index = 0
        #EAB1 = new line
        #EAB2/EAB3 = bold
        #EAB4/EAB5 = italic
        #EAB8/EABB = "copy-whatever's-in-this-to-the-Input-Field hyperlinks"
        #coloured text:
        #"EAC1 followed by two characters with the highest-order bit 1 and the lowest-order 12 bits 
        #  representing the first/second halves of a 24-bit RGB color value to start the range, EAC2 to end. 
        #  So to render a character in green, for example, you'd want EAC1 800F 8F00, then the character, then EAC2."
        #  8CCC 8CCC
        #---
        #UTF-8: U+EAB1 = '\xee\xaa\xb1'
        self.TAG_NEW_LINE = '\xEE\xAA\xB1'.decode('utf-8')
        self.TAG_START_BOLD = '\xEE\xAA\xB2'.decode('utf-8')
        self.TAG_STOP_BOLD = '\xEE\xAA\xB3'.decode('utf-8')
        self.TAG_START_ITALIC = '\xEE\xAA\xB4'.decode('utf-8')
        self.TAG_STOP_ITALIC = '\xEE\xAA\xB5'.decode('utf-8')
        self.TAG_START_LINK = '\xEE\xAA\xB8'.decode('utf-8')
        self.TAG_STOP_LINK = '\xEE\xAA\xBB'.decode('utf-8')

    def remove_html_tags(self, string):
   
        string = re.sub(ur'\[b\](.+?)\[/b\]', self.TAG_START_BOLD+r'\1'+self.TAG_STOP_BOLD, string)
        string = re.sub(self.TAG_START_BOLD+'(I|V|X)', self.TAG_NEW_LINE*2+self.TAG_START_BOLD+ur'\1', string)

        string = re.sub(r'\[m[1-9]\]\[\*\]\[ex\]', self.TAG_NEW_LINE, string)
        string = re.sub(r'\[(ex|e)\]', self.TAG_NEW_LINE, string)
        string = re.sub(r'\[m2\]', self.TAG_NEW_LINE*2, string)
        string = re.sub(r'\[m[3-9]\]', self.TAG_NEW_LINE, string)

        string = string.replace('\]',']')
        string = string.replace('\[','[')
        string = re.sub(self.TAG_NEW_LINE+r'([0-9]+\))', self.TAG_NEW_LINE+self.TAG_START_BOLD+r'\1'+self.TAG_STOP_BOLD, string)
        string = string.replace('\ ',' ')
        string = string.replace('*',' ')


        string = re.sub(r'\[[a-zA-Z0-9/ ]+\]', ' ', string)
        string = re.sub(r'[ ]+', ' ', string)
        string = re.sub(r'^[ ]+([^ ].+?)$', r'\1', string)
        
        string = re.sub(r'[ ]+'+self.TAG_NEW_LINE, self.TAG_NEW_LINE, string)
        string = re.sub('^['+self.TAG_NEW_LINE+']+', self.TAG_NEW_LINE, string)
        string = re.sub(self.TAG_NEW_LINE+r'[ ]+?', self.TAG_NEW_LINE, string)

        return string

    def create_db(self):
        self.parent.log('Create pleco db')
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
        self.cursor.execute('INSERT INTO pleco_dict_properties VALUES(0,"EditLock",1,0);')
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

    def write_db(self, word, trad_word, pronounce, translate):
        ctime = str(int(time.time()))
        wordlen = len(word)
        translate = translate
        first_pron = pronounce.split(',')[0]
        sortindex = first_pron+word
        try:
            self.cursor.execute('INSERT INTO pleco_dict_entries VALUES (NULL,?,?,?,?,?,?,?,?)', (ctime, ctime, wordlen, word, trad_word, pronounce, translate, sortindex))
            self.db_last_insert_id = self.cursor.lastrowid
        except:
            self.parent.log('DB Error: '+str(sys.exc_info()[0])+' word: '+word)

        self.buffer_index += 1
        if self.buffer_index > self.BUFFER_SIZE:
            self.buffer_index = 0
            self.conn.commit()
    def create_db_word_index(self, ob_pron, wordlen):
        pronounciations = []
        list_pron = []
        for pron in ob_pron:
            i = 0
            for hanzi, num_pinyin, sep in pron:
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
        self.parent.log('Create pleco db index')
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