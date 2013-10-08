'''
Created on 24/09/2013

@author: jc.forero47
'''
#----------------------------------------------------------------- import urllib
#--------------------------------------------------------------- import httplib2
#------------------------------------------------------------------- import json
#------------------------------------------------------------------------------ 
#------------------------------------------------------------------- query = """
#---------------------------------- PREFIX dc:<http://purl.org/dc/elements/1.1/>
#--------------------------- PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
#-------------------------------------- PREFIX foaf:<http://xmlns.com/foaf/0.1/>
#----------------------------------- PREFIX owl:<http://www.w3.org/2002/07/owl#>
#-------------------------------- PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
#---------------------- PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
#-------------------------- PREFIX vcard:<http://www.w3.org/2001/vcard-rdf/3.0#>
#------------------------------------ PREFIX dcterms:<http://purl.org/dc/terms/>
# PREFIX braint:<http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53#>
#--------------------------------------------------------------- select ?x ?y ?z
#-------------------------------------------------------------- where{ ?x ?y ?z}
#------------------------------------------------------------------------- # """
#------------------------------------------------------- repository = 'pythonBD'
# endpoint = "http://localhost:8080/openrdf-sesame/repositories/%s" % (repository)
#------------------------------------------------------------------------------ 
#------------------------------- print "POSTing SPARQL query to %s" % (endpoint)
#--------------------------------------------------- params = { 'query': query }
#------------------------------------------------------------------- headers = {
  #------------------------ 'content-type': 'application/x-www-form-urlencoded',
  #--------------------------------- 'accept': 'application/sparql-results+json'
#----------------------------------------------------------------------------- }
# (response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
#------------------------------------------------------------------------------ 
#----------------------------------------- print "Response %s" % response.status
#------------------------------------------------- results = json.loads(content)
#------------------------------------------ print results['results']['bindings']
#------------------------------------- print len(results['results']['bindings'])
#-------------------------------------- miLista = results['results']['bindings']
#-------------------------------------------------------- for miItem in miLista:
    #--------------------------------------------- xValue = miItem['x']['value']
    #------------------------------------ xVal,xSep,xAft = xValue.partition('#')
    #--------------------------------------------- yValue = miItem['y']['value']
    #------------------------------------ yVal,ySep,yAft = yValue.partition('#')
    #--------------------------------------------- zValue = miItem['z']['value']
    #------------------------------------ zVal,zSep,zAft = zValue.partition('#')
    #----------------------------------- print xAft  + '\t' + yAft + '\t' + zAft
    # #===========================================================================
    #----------------------------------- # for key, value in miItem.iteritems():
    #------------------------- #     response = response + value['value'] + '\t'
    # #===========================================================================
#------------------------------------------------------------------------------ 
#------------------------------------------------------------------------------ 
import urllib
import httplib2
import json
 
query = """
PREFIX dc:<http://purl.org/dc/elements/1.1/>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>
PREFIX foaf:<http://xmlns.com/foaf/0.1/>
PREFIX owl:<http://www.w3.org/2002/07/owl#>
PREFIX xsd:<http://www.w3.org/2001/XMLSchema#>
PREFIX rdf:<http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX vcard:<http://www.w3.org/2001/vcard-rdf/3.0#>
PREFIX dcterms:<http://purl.org/dc/terms/>
PREFIX braint:<http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53#>
SELECT  ?Evaluation ?Test ?SubTest ?SubSubTest
WHERE { 
  ?X braint:Evaluation_Name ?Evaluation .
  OPTIONAL {?X braint:hasTest ?Test}   
  OPTIONAL {?Test braint:hasSubTest ?SubTest} .
  OPTIONAL {?SubTest braint:hasSubSubTest ?SubSubTest }
}
# """
repository = 'pythonBD'
endpoint = "http://localhost:8080/openrdf-sesame/repositories/%s" % (repository)
 
print "POSTing SPARQL query to %s" % (endpoint)
params = { 'query': query }
headers = { 
  'content-type': 'application/x-www-form-urlencoded', 
  'accept': 'application/sparql-results+json' 
}
(response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
  
print "Response %s" % response.status
results = json.loads(content)
print results['results']['bindings']
print len(results['results']['bindings'])
miLista = results['results']['bindings']
for miItem in miLista:
    xValue = miItem['Evaluation']['value']
    xVal,xSep,xAft = xValue.partition('#')
    yValue = miItem['Test']['value']
    yVal,ySep,yAft = yValue.partition('#')
    zValue = miItem['SubTest']['value']
    zVal,zSep,zAft = zValue.partition('#')
    if 'SusSubTest' in miItem:
        wValue = miItem['SubSubTest']['value']
        wVal,wSep,wAft = wValue.partition('#')
        print xAft  + '\t' + yAft + '\t' + zAft + '\t' + wAft
    else:
        print xAft  + '\t' + yAft + '\t' + zAft + 'NO HAY W'
    #===========================================================================
    # for key, value in miItem.iteritems():
    #     response = response + value['value'] + '\t'
    #===========================================================================




