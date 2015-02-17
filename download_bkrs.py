# -*- coding: utf-8 -*-
from subprocess import call
import urllib2
import re
from os.path import expanduser

home = expanduser("~")
site = 'http://bkrs.info/'
page_url = site+'p47'
pagedata = urllib2.urlopen(url=page_url, timeout=3000).read()
matched = re.findall('downloads/daily/dabkrs_[0-9]{6}\.gz', pagedata)[0]
name = re.findall('dabkrs_[0-9]{6}', matched)[0]
url = site+matched
print 'finded bkrs db file: '+url
print 'name: '+name
idir = home+'/dev/BKRStoPleco/input_files/'
cmd1 = "wget -O "+idir+"bkrs.gz "+url
cmd2 = "gunzip "+idir+"bkrs.gz"
cmd3 = "mv "+idir+"bkrs "+idir+"bkrs_last.txt"
call(cmd1.split())
call(cmd2.split())
call(cmd3.split())
