#!/usr/bin/env python3

# Copyright (C)2015 Marcus Soll
#
# jmdict-to-sqlite3 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jmdict-to-sqlite3 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with jmdict-to-sqlite3. If not, see <http://www.gnu.org/licenses/>.

# todo, remove sep
# group each kanji and meaning

import sys
import os
import time
import sqlite3
import xml.etree.ElementTree
import copy

def jmdict_to_sqlite3(input, output):
    """
    Transforms a JMDict-XML-file to a SQLite3-database
    :param input: Path to input XML file
    :type input: str
    :param output: Path to output SQLite3 file
    :type: output: str
    :param lang: If lang is set the language will be used instead of english if possible
    :type lang: str
    :return: None
    """
    #if lang=en is used we unset lang for standard behaviour
    # if lang =='eng':
    #     lang = ''

    print('Input file: %s' % input)
    print('Output file: %s' % output)
    # if lang != '':
    #     print('Using lang: %s' % lang)

    if not os.path.isfile(input):
        raise IOError('Input file %s not found' % input)
        return

    if os.path.exists(output):
        raise IOError('Output file %s already exists' % output)
        return

    print('Converting...')

    #Counter
    converted = 0
    not_converted = 0

    #Connect to database
    connection = sqlite3.connect(output)
    cursor=connection.cursor()

    cursor.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE entry (word_first TEXT, words TEXT, details TEXT, freq TEXT)')

    connection.commit()

    #Creating metadata
    #cursor.execute("INSERT INTO meta VALUES ('license', 'CC-BY-SA 4.0 International')")
    cursor.execute("INSERT INTO meta VALUES ('license', 'CC-BY-SA 3.0 Unported')")
    cursor.execute("INSERT INTO meta VALUES ('database date of creation', ?)", (time.strftime('%Y-%m-%d'),))

    #Open JMDict
    element_tree = xml.etree.ElementTree.parse(input)
    root = element_tree.getroot()

    #Parsing

    myDict = {}

    for entry in root.findall('entry'):
        id = 0
        word_first = ''
        words = ''
        details = ''
        freq = ''

        sep = 0

        details += '<div class="jmdict-entry">\n'

        for value in entry.iter():

            if value.tag == 'ent_seq':
                id = value.text

            elif value.tag == 'k_ele':

                # get words
                for k_ele in value.findall('keb'):
                    # word_first
                    if word_first == '':
                        word_first = k_ele.text

                    # all words, word_first + alternatives
                    words += k_ele.text + ' '

                details += '    <div class="word">' + k_ele.text + '</div>\n'

                # get frequency tags
                for ke_pri in value.findall('ke_pri'):
                    freq += ke_pri.text + ' '


            elif value.tag == 'r_ele':

                # separator between words and readings
                if sep == 0:
                    details += '    <div class="sep"></div>\n'
                    sep = 1

                for r_ele in value.findall('reb'):
                    if r_ele.find('re_restr') is None:
                        details += '    <div class="reading">' + r_ele.text + '</div>\n'

                        # If it's a kana only word, put the reading as the key word.
                        if words == '':
                            words = r_ele.text
                        if word_first == '':
                            word_first = r_ele.text


            elif value.tag == 'sense':
                details += '    <div class="sense">\n'

                details += '        <div class="misc">\n'
                for misc in value.findall('misc'):
                    details += '            <span>' + misc.text + '</span>\n'
                details += '        </div>\n'
    
                details += '        <div class="field">\n'
                for field in value.findall('field'):
                    details += '            <span>' + field.text + '</span>\n'
                details += '        </div>\n'

                details += '        <div class="dial">\n'
                for dial in value.findall('dial'):
                    details += '            <span>' + dial.text + '</span>\n'
                details += '        </div>\n'

                details += '        <div class="pos">\n'
                for pos in value.findall('pos'):
                    details += '            <div>' + pos.text + '</div>\n'
                details += '        </div>\n'

                details += '        <ol class="gloss">\n'
                for gloss in value.findall('gloss'):
                    details += '            <li>' + gloss.text + '</li>\n'
                details += '        </ol>\n'

                details += '    </div>\n'

        details += '</div>\n'

        if word_first not in myDict:
            # if it's a new element, we'll create
            myDict[word_first] = {};
            myDict[word_first]["words"] = words;
            myDict[word_first]["id"] = id;
            myDict[word_first]["details"] = details;
            myDict[word_first]["freq"] = freq;
        else:
            # if it's not a new element, we'll concatenate existing details
            myDict[word_first]["details"] += details;
            myDict[word_first]["freq"] += freq;

    # create duplicate rows if it has multiple way to write in kanji.
    # this part is useful if you want to update an existing anki deck that uses alternative form
    # NOTE: comment this section if you want each row to have unique "details" field
    myDictOriTemp = copy.deepcopy(myDict)
    for key, value in myDictOriTemp.iteritems():
        words = value["words"].split()
        for valueInner in words:
            # valueInner is each of the alternative writing
            if valueInner not in myDict:
                myDict[valueInner] = copy.deepcopy(myDictOriTemp[key])
            elif key != valueInner:
                # if it's already exist, but from different key row, we'll concatenate existing details
                myDict[valueInner]["details"] += value["details"];
                myDict[valueInner]["freq"] += value["freq"];


    # execute SQLs from myDict
    for key, value in myDict.iteritems():
        # key is the word_first itself
        # values is myDict[key]

        if value["id"] != 0 :
            converted += 1
            cursor.execute('INSERT INTO entry VALUES (?, ?, ?, ?)', (key, value["words"], value["details"], value["freq"]))
        else:
            not_converted += 1

    connection.commit()
    connection.close()
    print('Converting done!')
    print('Converted entries: %i' % converted)
    print('Not converted entries: %i' % not_converted)
    return

#A simple starting wrapper
if __name__ == '__main__':
    if len(sys.argv[1:]) != 2:
        print('Please specify exactly two arguments:')
        print('- First the input JMDict file')
        print('- Second the output SQLite3 file')
        sys.exit(0)

    try:
        jmdict_to_sqlite3(sys.argv[1], sys.argv[2])
    except KeyboardInterrupt:
        print('\nAborted')
        sys.exit(0)
