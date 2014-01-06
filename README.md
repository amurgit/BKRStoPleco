BKRStoPleco
==========

Скрипт конвертации базы [BKRS](http://bkrs.info/) в формат словаря [Pleco] (http://pleco.com/).

Для начала работы с базой, её нужно скачать с сайта БКРС (http://bkrs.info/p47) файл 大БКРС vxxxxxxx, НЕ в dsl формате.
затем установить python (http://python.org) версию 2.7, затем установить библиотеку cjklib (http://cjklib.org/0.3/) 
и с помощью библиотеки cjklib установить словарь CEDICT.
Закинуть скрипт и файл базы данных в одну папку и запустить скрипт.
Если не меняли параметры, то в результате появятся файлы:
* bkrs.pqb - файл словаря в Pleco формате
* BKRS_bad_words.html - файл с возможными ошибками в пиньине
* log_file.txt - файл служебного лога

BKRS_bad_words.html
-----------------------
Поля в таблице: 
Number  - порядковый номер ошибки и номер строки в файле бд_бкрс
Error 	- описание ошибки, сейчас почти всегда рдно и тоже, можно не обращать внимание
Hanzi 	- само слово, ссылка на сайт бкрс
Pinyin 	- оригинальный пиньин
Corrected pinyin - пиньин из в котором подсвечены красным цветом символы, которые не должны быть в поле_пиньин
Pinyin match - совпавшие иероглифы и произношение, которые скрипт нашел к ним
Pinyin Not match - проблемный иероглиф и варианты произношений, которые есть для этого иероглифа
Translate - первые 50 символов из перевода

Имеет смысл отсортировать слова по полю "Pinyin Not match" и исправлять похожие ошибки.
Также в файле log_file.txt можно посмотреть иероглифы, в которых наиболее часто допускаются ошибки.

Чтобы пользоваться пользовательскими словарями в Pleco нужен установленый модуль флешкарт, 
сейчас для андроид версии этот модуль платный. 

Пояснение работы скрипта
------------------------

Скрипт пытается для пиньина подобрать соответсвие с возможными произношениями иероглифов.
Возможные произношения берутся из cjklib и из CEDICT. В словарь записывает только слова с русским переводом 
и найденым сопоставлением произношения. 
В файле ошибок пиньина каждая запись - это необязательно ошибка, так как есть старые произношения и т.п.
Скрипт естественно не находит всех ошибок пиньина, но он находит самые очевидные.
Не найдет ошибки если перепутали тон. Так же не найдет ошибки если 
указали не то произношения иероглифа которое на самом деле в слове 
например для иероглифа cjklib 没 есть два возможных произношения: méi, mò и вы в пиньине вместо mò написали méi.

Скрипт довольно медленный и на всей базе ~2 000 000 слов на моем ноутбуке отрабатывает 
за час и десять минут.

по вопросам и предложениям связанным с скриптом пожайлуйте в форум БКРС к пользователю alexamur
