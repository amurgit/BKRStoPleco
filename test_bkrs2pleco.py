# -*- coding: utf-8 -*-
from bkrs2pleco import BKRS2DB
import unittest


class TestBKRS2DB (unittest.TestCase):

	@classmethod
	def setUpClass(self):
		#self.bkrs = BKRS2DB(configfile = 'input_files/config.ini')
		self.bkrs = BKRS2DB(configfile = 'input_files/test/config.ini')
		self.bkrs.load_additional_pronounces()
		self.bkrs.load_character_frequency()

	def test_join_nonprintable_hanzi(self):
		self.assertEqual(self.bkrs.join_nonprintable_hanzi(u'巴戛鱼岁'), u'巴戛鱥')

	def test_get_hanzi_freq(self):
		self.assertGreater(self.bkrs.get_hanzi_freq(u'学'), 3949)
		self.assertEqual(self.bkrs.get_hanzi_freq(u'学学'), 1)
		self.assertGreater(self.bkrs.get_hanzi_freq(u'子'), 6791)
		self.assertGreater(self.bkrs.get_hanzi_freq(u'洗'), 453)

	def test_get_word_freq(self):
		self.assertGreater(self.bkrs.get_word_freq(u'学习'), 2124)

	def test_hanziword_have_comma(self):
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学，习'), True)
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学﹐习'), True)
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学，习'), True)
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学，习'), True)
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学:习'), False)
		self.assertEqual(self.bkrs.hanziword_have_comma(u'学:习'), False)

	def test_have_tag_symbol(self):
		self.assertEqual(self.bkrs.have_tag_symbol(u'sān [ref]dà[/ref] yáng'), True)
		self.assertEqual(self.bkrs.have_tag_symbol(u'sān dà yáng'), False)


	def test_pinyin_highlight_bad_sybmols(self):
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'fēngyún，dì yǒu'), u'fēngyún<b class="red">(，)</b>dì yǒu')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'fēng yĭ'), u'fēng y<b class="red">(ĭ)</b>')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'sù В2'), u'sù <b class="red">(В2)</b>')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'bù mǎn 18 zhōusuì de rén'), u'bù mǎn <b class="red">(18)</b> zhōusuì de rén')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'tuō‧huá'), u'tuō<b class="red">(‧)</b>huá')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'	abc fēnxī'), u'<b class="red">(	)</b>abc fēnxī')
		self.assertEqual(self.bkrs.pinyin_highlight_bad_sybmols(u'ā’ěrtàishān'), u'ā’ěrtàishān')

	def test_word_highlight_bad_sybmols(self):
		self.assertEqual(self.bkrs.word_highlight_bad_sybmols(u'Ｑ开关激光器'), u'<b class="red">(Ｑ)</b>开关激光器')
		self.assertEqual(self.bkrs.word_highlight_bad_sybmols(u'开-关激光器'), u'开-关激光器')
		self.assertEqual(self.bkrs.word_highlight_bad_sybmols(u'不...不...'), u'不<b class="red">(...)</b>不<b class="red">(...)</b>')

	def test_replace_tags_with_content(self):
		self.assertEqual(self.bkrs.replace_tags_with_content(u'[c][i]уст.[/i][/c] Три округа'), u' Три округа')
		self.assertEqual(self.bkrs.replace_tags_with_content(u'dāi;[c][i] kнижн.[/c] [c][/i][/c]ái'),u'dāi;ái')

	def test_translate_have_rus(self):
		self.assertEqual(self.bkrs.translate_have_rus(u'[m1]читать что попало, смотреть куда попало[/m]'), True)
		self.assertEqual(self.bkrs.translate_have_rus(u'[m1][i]читать[i][/m]'), True)
		self.assertEqual(self.bkrs.translate_have_rus(u'[p]диал.[/p] [ref]墩子[/ref]'), False)

	def test_hanziword_have_comma(self):
		self.assertEqual(self.bkrs.hanziword_have_comma(u'三，无'),True)

	def test_replace_comma(self):
		self.assertEqual(self.bkrs.replace_comma(u'学，习',''), u'学习')
		self.assertEqual(self.bkrs.replace_comma(u'学﹐习',''), u'学习')
		self.assertEqual(self.bkrs.replace_comma(u'学，习',''), u'学习')
		self.assertEqual(self.bkrs.replace_comma(u'学，习',' '), u'学 习')
		self.assertEqual(self.bkrs.replace_comma(u'学:习'), u'学:习')
		self.assertEqual(self.bkrs.replace_comma(u'学习'), u'学习')
		self.assertEqual(self.bkrs.replace_comma(u'tuō‧huá'), u'tuō‧huá')
		self.assertEqual(self.bkrs.replace_comma(u'sān,wú', ' '), u'sān wú')
		self.assertEqual(self.bkrs.replace_comma(u'ā’ěrtàishān', ' '), u'ā’ěrtàishān')

	def test_get_with_tone_mark(self):
		self.assertEqual(self.bkrs.get_with_tone_mark(u'san1'),u'sān')

	def test_get_cedict_pron_variants(self):
		self.assertEqual(self.bkrs.get_cedict_pron_variants(u'戛'),[u'jiá'])
		#self.assertEqual(self.bkrs.get_cedict_pron_variants(u'账'),[u'jiá'])

	def test_get_pron_variants(self):
		self.assertEqual(self.bkrs.get_pron_variants(u'戛'), [u'jiá', u'gā'])
		self.assertEqual(self.bkrs.get_pron_variants(u'齐'), [u'jì', u'qí', u'zhāi', u'zī'])
		self.assertEqual(self.bkrs.get_pron_variants(u'3'),[u'sān', '3'])
		self.assertEqual(self.bkrs.get_pron_variants(u'2'),[u'èr',u'liǎng','2'])
		self.assertEqual(self.bkrs.get_pron_variants(u'缩'),[u'sù',u'suō'])
		self.assertEqual(self.bkrs.get_pron_variants(u'*'),[])
		self.assertEqual(self.bkrs.get_pron_variants(u'一'),[ u'yī', u'yí', u'yì', u'yāo'])
		#self.assertEqual(self.bkrs.get_pron_variants(u'账'),[u'',u''])

	def test_get_with_mixed_tones(self):
		self.assertEqual(self.bkrs.get_with_mixed_tones([u'sān']),[u'sān',u'sán',u'sǎn',u'sàn',u'san'])
		self.assertEqual(self.bkrs.get_with_mixed_tones([u'sān', u'ān'], True),[u'sān',u'sán',u'sǎn',u'sàn',u'san',u'ān',u'án',u'ǎn',u'àn',u'an'])

	
	def test_pinyin_have_bad_symbol(self):
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'16把机械手刀库'),False)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'ā’ěrtàishān'),False)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'α-亚麻酸'),False)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'​'),True) #not visible symbol
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'​·'),True)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'/​'),True)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u'　'),True)
		self.assertEqual(self.bkrs.pinyin_have_bad_symbol(u' '),False)

	def test_filter_pinyin(self):
		self.assertEqual(self.bkrs.filter_pinyin(u'mā lă; mǎ,(soso) ‘ko’_lo`to-no'), u'mā lǎ,mǎ,ko’_lo to no')
		self.assertEqual(self.bkrs.filter_pinyin(u'qí [c][i]диaл. kнижн. тakжe[/c] [c][/i][/c]xí'),u'qí,xí')
		self.assertEqual(self.bkrs.filter_pinyin(u'zhūn; chún; [c][i]в coчeт. тakжe[/i][/c] tún'),u'zhūn,chún,tún')
		self.assertEqual(self.bkrs.filter_pinyin(u'xì; xiè'),u'xì,xiè')
		self.assertEqual(self.bkrs.filter_pinyin(u'zào; [c][i]в coчeт. тakжe[/i][/c] sào'),u'zào,sào')
		self.assertEqual(self.bkrs.filter_pinyin(u'kuí;[c][i] kнижн.[/c] [c][/i][/c]kuǐ'),u'kuí,kuǐ')
		self.assertEqual(self.bkrs.filter_pinyin(u'piān;[c][i] вм.[/i][/c] 稨 [c][i]и в coчeт. тakжe[/c] [c][/i][/c]biān; biǎn'),u'piān,稨,biān,biǎn')
		self.assertEqual(self.bkrs.filter_pinyin(u'kē; ké;[c][i] ycт.[/i][/c] hái'),u'kē,ké,hái')
		self.assertEqual(self.bkrs.filter_pinyin(u'bù mǎn 18 zhōusuì de rén'),u'bù mǎn 18 zhōusuì de rén')
		self.assertEqual(self.bkrs.filter_pinyin(u'bù  mǎn'),u'bù mǎn')
		self.assertEqual(self.bkrs.filter_pinyin(u'dāi;[c][i] kнижн.[/c] [c][/i][/c]ái'),u'dāi,ái')
		self.assertEqual(self.bkrs.filter_pinyin(u'yǔqí... bùrú...'),u'yǔqí bùrú')
		self.assertEqual(self.bkrs.filter_pinyin(u'bái luóbo zhā dāozi —— bù chū xiě de dōngxi'),u'bái luóbo zhā dāozi bù chū xiě de dōngxi')
		self.assertEqual(self.bkrs.filter_pinyin(u'shūrù/shūchū'),u'shūrù shūchū')
		self.assertEqual(self.bkrs.filter_pinyin(u'bèinítuō‧huáléisī'),u'bèinítuō huáléisī')
		self.assertEqual(self.bkrs.filter_pinyin(u'bā xiān zhuōzi gài jíngkǒu – suí fāng'),u'bā xiān zhuōzi gài jíngkǒu suí fāng')
		self.assertEqual(self.bkrs.filter_pinyin(u'gōngyì fāng\ àn'),u'gōngyì fāng àn')
		self.assertEqual(self.bkrs.filter_pinyin(u'dòufu – ruǎn '),u'dòufu ruǎn')
		self.assertEqual(self.bkrs.filter_pinyin(u'ā’ěrfǎ yàmásuān'),u'ā’ěrfǎ yàmásuān')
		self.assertEqual(self.bkrs.filter_pinyin(u'ā’ěrtàishān'),u'ā’ěrtàishān')
	
	def test_filter_hanzi(self):
		self.assertEqual(self.bkrs.filter_hanzi(u'桂,花-木,茸 '), u'桂花木茸')
		self.assertEqual(self.bkrs.filter_hanzi(u'911事件'), u'911事件')
		self.assertEqual(self.bkrs.filter_hanzi(u'3Q'), u'3Q')
		self.assertEqual(self.bkrs.filter_hanzi(u'维生素D2'), u'维生素D2')
		self.assertEqual(self.bkrs.filter_hanzi(u'道…不…'), u'道不')
		self.assertEqual(self.bkrs.filter_hanzi(u'白萝卜扎刀子——不出血的东西'), u'白萝卜扎刀子不出血的东西')
		self.assertEqual(self.bkrs.filter_hanzi(u'输入/输出'), u'输入输出')
		self.assertEqual(self.bkrs.filter_hanzi(u'贝尼托‧华雷斯'), u'贝尼托华雷斯')
		self.assertEqual(self.bkrs.filter_hanzi(u'八仙桌子盖井口–随方就圆'), u'八仙桌子盖井口随方就圆')
		self.assertEqual(self.bkrs.filter_hanzi(u'ζ电势'), u'ζ电势')
		self.assertEqual(self.bkrs.filter_hanzi(u'α-亚麻酸'), u'α亚麻酸')

	def test_get_numeric_tone(self):
		self.assertEqual(self.bkrs.get_numeric_tone(u'sāngè'),'san1ge4')
		self.assertEqual(self.bkrs.get_numeric_tone(u'jiétǎ'),'jie2ta3')
		self.assertEqual(self.bkrs.get_numeric_tone(u'ā’ěrfǎ'),u'a1’er3fa3')
		self.assertEqual(self.bkrs.get_numeric_tone(u'ā’ěr fǎ'),u'a1’er3 fa3')

	def convert_to_num(self, hanzi, pinyin):
		return self.bkrs.get_string_pron(self.bkrs.convert_full_pinyin(hanzi, pinyin))

	def test_convert_full_pinyin(self):
		self.assertEqual(self.bkrs.convert_full_pinyin(u'三个', u'sāngè'), [[(u'三', u'san1' ,''), (u'个', u'ge4','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'三-个', u'sāngè'), [[(u'三', u'san1',''), (u'个', u'ge4','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'三-个', u'sān gè '), [[(u'三', u'san1',' '), (u'个', u'ge4','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'个', u'gè, ge'), [[(u'个', u'ge4','')],[(u'个', u'ge5','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'个', u'gè'), [[(u'个', u'ge4','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'三，无', u'sān,wú'), [[(u'三', u'san1',' '), (u'无', u'wu2','')]])
		self.assertEqual(self.bkrs.convert_full_pinyin(u'唳，草', u'lì,cǎo'), [[(u'唳', u'li4',' '), (u'草', u'cao3','')]])

		self.assertEqual(self.convert_to_num(u'差额账', u'chā’ ézhàng'), u'')
		self.assertEqual(self.convert_to_num(u'亗', u'suì'), u'sui4')
		self.assertEqual(self.convert_to_num(u'阿尔泰山', u'ā’ěrtàishān'), u'a1’er3tai4shan1')
		self.assertEqual(self.convert_to_num(u'α-亚麻酸', u'ā’ěrfǎ yàmásuān'), u'a1’er3fa3 ya4ma2suan1')
		self.assertEqual(self.convert_to_num(u'ζ电势', u'jiétǎ diànshì'), 'jie2ta3 dian4shi4')
		self.assertEqual(self.convert_to_num(u'ζ电势', u'jiétǎdiànshì'), 'jie2ta3dian4shi4')
		self.assertEqual(self.convert_to_num(u'ζ电势', u'zetadiànshì'), 'zetadian4shi4')
		self.assertEqual(self.convert_to_num(u'ζ电势', u'diànshì'), '')
		self.assertEqual(self.convert_to_num(u'手：罪', u'shǒu: zuì'), 'shou3 zui4')
		self.assertEqual(self.convert_to_num(u'大宗买卖', u'dàzōng mǎi·mai'), 'da4zong1 mai3 mai5')
		self.assertEqual(self.convert_to_num(u'911事件', u'jiǔyāoyāoshìjiàn'), 'jiu3yao1yao1shi4jian4')
		self.assertEqual(self.convert_to_num(u'911事件', u'jiǔ yāo yāo shìjiàn'), 'jiu3 yao1 yao1 shi4jian4')
		self.assertEqual(self.convert_to_num(u'0748', u'líng qī sì bā'), 'ling2 qi1 si4 ba1')
		self.assertEqual(self.convert_to_num(u'521', u'wǔ èr yī'), 'wu3 er4 yi1')
		self.assertEqual(self.convert_to_num(u'维生素d2', u'wéishēngsù d2'), 'wei2sheng1su4 d2')
		self.assertEqual(self.convert_to_num(u'3Q', u'san q'), '')
		self.assertEqual(self.convert_to_num(u'4', u'sǐ'), '')
		self.assertEqual(self.convert_to_num(u'3Q', u'sān q'), 'san1 q')
		self.assertEqual(self.convert_to_num(u'BB机', u'bibi jī'), 'bibi ji1')
		self.assertEqual(self.convert_to_num(u'歼-10', u'jiān 10'), 'jian1 10')
		self.assertEqual(self.convert_to_num(u'AA制', u'a a zhì'), 'a a zhi4')
		self.assertEqual(self.convert_to_num(u'AB制', u'abzhì'), 'abzhi4')
		self.assertEqual(self.convert_to_num(u'的500种', u'de 500 zhǒng'), 'de5 500 zhong3')
		self.assertEqual(self.convert_to_num(u'985工程', u'985 gōngchéng'), '985 gong1cheng2')
		self.assertEqual(self.convert_to_num(u'ABC分析法', u'abc fēnxī fǎ'), 'abc fen1xi1 fa3')
		self.assertEqual(self.convert_to_num(u'网络IP电话', u'wǎngluò ip diànhuà'), 'wang3luo4 ip dian4hua4')
		self.assertEqual(self.convert_to_num(u'难道...不成', u'nándao…buchéng'), 'nan2dao5 bu5cheng2')
		self.assertEqual(self.convert_to_num(u'白萝卜扎刀子——不', u'bái luóbo zhā dāozi —— bù'), 'bai2 luo2bo5 zha1 dao1zi5 bu4')
		self.assertEqual(self.convert_to_num(u'道…不…', u'dào…bù…'), 'dao4 bu4')
		self.assertEqual(self.convert_to_num(u'与其不如', u'yǔqí... bùrú...'), 'yu3qi2 bu4ru2')
		self.assertEqual(self.convert_to_num(u'计划', u'jìhuà'), 'ji4hua4')
		self.assertEqual(self.convert_to_num(u'缩', u'sūo'), 'su1')
		self.assertEqual(self.convert_to_num(u'缩', u'suō'), 'suo1')
		self.assertEqual(self.convert_to_num(u'铀浓缩计划', u'yóunóngsuō jìhuà'), 'you2nong2suo1 ji4hua4')
		self.assertEqual(self.convert_to_num(u'雷公打豆腐–软处下手', u'léigōng dǎ dòufu – ruǎn chù xià shǒu'), 'lei2gong1 da3 dou4fu5 ruan3 chu4 xia4 shou3')
		self.assertEqual(self.convert_to_num(u'呕暖', u'ǒunuǎn,ǒunuan'), 'ou3nuan3, ou3nuan5')
		self.assertEqual(self.convert_to_num(u'士', u'tǔ'), '') 
		self.assertEqual(self.convert_to_num(u'账', u'zhàng'), 'zhang4') 

		#self.assertEqual(self.convert_to_num(u'20国集团', u'èrshíguó jítuán'), 'er4 shi2 guo2 ji2 tuan2')
		#self.assertEqual(self.convert_to_num(u'旧金山49人', u'jiùjīnshān sìshíjiǔrén'), 'jiu4 jin1 shan1 si4 shi2 jiu3 ren2')
		#self.assertEqual(self.convert_to_num(u'百一非', u'bǎi fēi'), 'bai3 fei1')
		#self.assertEqual(self.convert_to_num(u'青霉素一鱼素', u'qīngméisù-yúsù '), 'qing1mei2su4 yu2su4')
		#self.assertEqual(self.convert_to_num(u'咬十', u'yǎo,shí'), 'yao3 shi2')
		#self.assertEqual(self.convert_to_num(u'ζ电势', u'ζ diànshì'), 'dian4shi4')

	def test_export(self):
		self.bkrs.export()
		#pass

if __name__ == "__main__":
	unittest.main()
