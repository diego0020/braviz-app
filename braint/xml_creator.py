__author__ = 'jc.forero47'

import Tkinter as tk
from Tkinter import Frame as tkFrame
from braviz.utilities import working_directory
import os.path as os_path
import subprocess
import sys
import tkFont
from kernel.RDFDBManagerClass import *
myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
listResults=myManager.loadQuery('File\\rdfqueries\IdAndNames')

relations_xml_file = open('testfile.xml', 'w')

relations_xml_file.write('<vertex name="">\n')
print listResults
items_add = dict()
for my_item in listResults:
    evaluation_name = my_item['Evaluation']['value']
    if evaluation_name not in items_add:
        items_add.update({evaluation_name : dict()})

    test_dict = items_add[evaluation_name]
    if 'Test' in my_item:
        raw_test_id = my_item['Test']['value']
        wVal,wSep,test_id = raw_test_id.partition('#')
        if test_id not in test_dict:
            test_dict.update({test_id : dict()})
        if 'SubTest' in my_item:
            raw_subtest_id = my_item['SubTest']['value']
            wVal,wSep,subtest_id = raw_subtest_id.partition('#')
            subtest_dict = test_dict[test_id]
            if subtest_id not in subtest_dict:
                subtest_dict.update({subtest_id : list()})

            if 'SubSubTest' in my_item:
                raw_subsubtest_id = my_item['SubSubTest']['value']
                wVal,wSep,subsubtest_id = raw_subsubtest_id.partition('#')
                subsubtest_list = subtest_dict[subtest_id]
                if subsubtest_id not in subsubtest_list:
                    subsubtest_list.append(subsubtest_id)
    #    if subsubtest_id not in items_add:ic
    #        list_id_subtest=items_add[subtest_id]
    #        node_name = subsubtest_id + '-'
    #        if 'SubSubTestName' in my_item:
    #            subsubtest_name=my_item['SubSubTestName']['value']
    #            node_name = node_name + subsubtest_name
    #        items_add.update({subsubtest_id})

print items_add
#Create the xml file
for eval in items_add.keys():
    relations_xml_file.write('\t<vertex name="' + eval + '">\n')
    test_add = items_add[eval]
    for test in test_add.keys():
        relations_xml_file.write('\t\t<vertex name="' + test + '">\n')
        subtest_add = test_add[test]
        for subtest in subtest_add.keys():
            relations_xml_file.write('\t\t\t<vertex name="' + subtest + '">\n')
            subsubtest_add = subtest_add[subtest]
            for subsubtest in subsubtest_add:
                relations_xml_file.write('\t\t\t\t<vertex name="' + subsubtest + '"/>\n')
            relations_xml_file.write('\t\t\t</vertex>\n')
        relations_xml_file.write('\t\t</vertex>\n')
    relations_xml_file.write('\t</vertex>\n')
relations_xml_file.write('</vertex>\n')

