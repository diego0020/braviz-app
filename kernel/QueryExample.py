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
import json
import urllib2
import urllib
import traceback
import sys 

def query(q,apikey,epr,f='application/json'):
    """Function that uses urllib/urllib2 to issue a SPARQL query.
       By default it requests json as data format for the SPARQL resultset"""

    try:
        params = {'query': q, 
                  'apikey': apikey,
 #                 'csrfmiddlewaretoken' : '8e241a744d2b70806cb21189cb1b0744'
                 }
        params = urllib.urlencode(params)
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(epr+'?'+params)
        request.add_header('Accept', f)
        request.get_method = lambda: 'GET'
        url = opener.open(request)
        return url.read()
    except Exception, e:
        traceback.print_exc(file=sys.stdout)
        raise e

if __name__ == "__main__":
    sparql_service = "http://sparql.bioontology.org/sparql/"

    #To get your API key register at http://bioportal.bioontology.org/accounts/new
    #api_key = "db57f859-4916-4bdb-b8c8-169206571e7b"
    api_key = "73f776e6-e21b-4bce-8420-24f9a3670dbb"
    #Some sample query.
    query_string = """ 
PREFIX radlex: <http://bioontology.org/projects/ontologies/radlex/radlexOwl#> 
SELECT ?codes ?names 
WHERE {
    ?codes radlex:Freesurfer ?name
    FILTER regex(?name, "G_frontal_inf-Orbital_part")
    ?codes radlex:Preferred_name ?names
}
LIMIT 1
"""
    json_string = query(query_string, api_key, sparql_service)
    resultset=json.loads(json_string)

    #Printing the json object.
    print json.dumps(resultset,indent=1)
