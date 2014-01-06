# -*- coding: utf-8 -*-
import lxml.html
from lxml import etree
import urllib2
import re
from cjklib.dictionary import CEDICT

def get_cedict_pron_variants(hanzi):
    pron_vars = []
    cedict = CEDICT()
    for entrie in cedict.getFor(hanzi):
        pron_vars.append(entrie.Reading)
    return pron_vars

bad_words = open('bad_words.txt', 'r');
html_out = open('bad_words.html', 'w', 100);

skip = 0

bkrsurl = 'http://bkrs.info/slovo.php?ch='
baiduurl = 'http://baike.baidu.com/search/word?word='
starthtml = """<html>
<head> 
    <meta charset="utf-8"/>
    <title>BKRS pinyin errors</title>
    <style>
a{text-decoration:none;}
.title{font-size: 24px;}
table{border: 1px solid #CCCCCC; width: 99%;}
td,th{border: 1px solid #CCC; padding: 4px 10px; text-align:left;}
    </style>
</head>
<body>
<p class="title"> BKRS pinyin errors</p>
<table class="etable" style="margin:0 auto; border-collapse: collapse; border-spacing: 0;" cellpadding="0" cellspacing="0">
        """
html_out.write(starthtml);

html_out.write('<tr>')
html_out.write('<th class="number">Num</td>')
html_out.write('<th class="hanziword">Hanziword</td>')
html_out.write('<th class="pinyin">Pinyin</td>')
html_out.write('<th class="bkrs_satpinyin">BKRS sat pinyin</td>')
html_out.write('<th class="cedict_pinyin">CEDICT pinyin</td>')
html_out.write('<th class="baike_url">Baike url</td>')
html_out.write('</tr>')

i = 0
for line in bad_words:
    i += 1
    if i<= skip:
        continue

    cedict_pinyin_list = []
    uline = line.decode('utf-8')
    hanziword = uline.split('\t')[0].encode('utf-8')
    pinyin = uline.split('\t')[1].encode('utf-8')

    bkrshtml = urllib2.urlopen(bkrsurl+hanziword).read()
    baiduhtml = urllib2.urlopen(baiduurl+hanziword).read()

    cedict_pinyin_list = get_cedict_pron_variants(hanziword.decode('utf-8'))
    cedict_pinyin = ', '.join(cedict_pinyin_list).encode('utf-8')

    bkrs_satpinyin = ''
    baike_url = ''
    baike_pinyin = ''
    baike_link = ''

    bkrs_matches =  re.findall("<div style='color:burlywood'>([^<]+)</div>",bkrshtml)
    if bkrs_matches:
        bkrs_satpinyin = ', '.join(bkrs_matches)

    baidu_matches = re.findall('<a href="([^"]+)" target="_blank"><em>'+hanziword+'</em>_百度百科</a>', baiduhtml)
    if baidu_matches:
        baike_url = baidu_matches[0]
        baike_link = '<a href="'+baike_url+'">'+baike_url+'</a>'

    print i

    html_out.write('<tr>')
    html_out.write('<td> #'+str(i)+'</td>')
    html_out.write('<td class="hanziword"><a href="'+bkrsurl+hanziword+'">'+hanziword+'</a></td>')
    html_out.write('<td class="pinyin">'+pinyin+'</td>')
    html_out.write('<td class="bkrs_satpinyin">'+bkrs_satpinyin+'</td>')
    html_out.write('<td class="cedict_pinyin">'+cedict_pinyin+'</td>')
    html_out.write('<td class="baike_link">'+baike_link+'</td>')
    html_out.write('</tr>')

html_out.write('</table></body></html>');
html_out.close()


