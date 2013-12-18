__author__ = 'jc.forero47'
from kernel.RDFDBManagerClass import *
myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
listResults=myManager.loadQuery('File\\rdfqueries\AllRelations')

relations_csv_file = open('testfilerelations.csv', 'w')
nodes_csv_file = open('testfilenodes.csv', 'w')

relations_csv_file.write('source,target\n')
nodes_csv_file.write('label\n')

print listResults
nodes_list = list()
for item in listResults:
    raw_source = item['source']['value']
    wVal,wSep,source = raw_source.partition('#')
    raw_target = item['target']['value']
    wVal,wSep,target = raw_target.partition('#')
    relations_csv_file.write(source + ',' + target + '\n')
    if source not in nodes_list:
        nodes_list.append(source)
    if target not in nodes_list:
        nodes_list.append(target)

for node in nodes_list:
    nodes_csv_file.write(node + '\n')