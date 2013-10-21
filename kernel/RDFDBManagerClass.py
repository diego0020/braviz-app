'''
Created on 24/09/2013

@author: jc.forero47
'''
import urllib
import httplib2
import json
import urllib2
import traceback
import sys 

class RDFDBManager:
    def __init__(self,repositoryName, graphName, RepositoryEndPoint): ##Constructor donde inicializo mis atributos de repositorio y grafo
       self.repository=repositoryName
       self.graph=graphName
       self.RepEndPoint=RepositoryEndPoint
       
    def loadRdf(self,filename):
        print "Loading %s into %s in Sesame" % (filename, self.graph)
        params = { 'context': '<' + self.graph + '>' }
        endpoint= "%s/openrdf-sesame/repositories/%s/statements?%s" % (self.RepEndPoint, self.repository, urllib.urlencode(params))
        #endpoint = "http://gambita.uniandes.edu.co:8080/openrdf-sesame/repositories/%s/statements?%s" % (self.repository, urllib.urlencode(params))
        data = open(filename, 'r').read()
        (response, content) = httplib2.Http().request(endpoint, 'PUT', body=data, headers={ 'content-type': 'text/turtle' })
        print "Response %s" % response.status
        print content
    def loadQuery(self,filename):
        data = open(filename, 'r').read()
        endpoint = "%s/openrdf-sesame/repositories/%s" % (self.RepEndPoint, self.repository)
        print "POSTing SPARQL query to %s" % (endpoint)
        params = { 'query': data }
        headers = { 
                   'content-type': 'application/x-www-form-urlencoded', 
                   'accept': 'application/sparql-results+json' 
                   }
        (response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
        print "Response %s" % response.status
        results = json.loads(content)
        print results
        print results['results']['bindings']
       #print len(results['results']['bindings'])
        miLista = results['results']['bindings']
        #=======================================================================
        # for miItem in miLista:
        #     xValue = miItem['x']['value']
        #     xVal,xSep,xAft = xValue.partition('#')
        #     yValue = miItem['y']['value']
        #     yVal,ySep,yAft = yValue.partition('#')
        #     zValue = miItem['z']['value']
        #     zVal,zSep,zAft = zValue.partition('#')
        #     print xAft  + '\t' + yAft + '\t' + zAft
        #=======================================================================
        return miLista #ME devuelve el diccionario con los resultados
    def loadQueryParentChildren(self,filename, parent, relation):
        data= open(filename, 'r').read()
        data=data.replace('PARENT_CODE', parent).replace('RELATION', relation)
        endpoint = "%s/openrdf-sesame/repositories/%s" % (self.RepEndPoint, self.repository)
        #print "POSTing SPARQL query to %s" % (endpoint)       
        params = { 'query': data }
        headers = { 
                   'content-type': 'application/x-www-form-urlencoded', 
                   'accept': 'application/sparql-results+json' 
                   }
        (response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
        #print "Response %s" % response.status
        results = json.loads(content)
       # print results
        #print results['results']['bindings']
        #print len(results['results']['bindings'])
        miLista = results['results']['bindings']
        childrenList = list()
        for miItem in miLista:
            xValue = miItem['Result']['value']
            xVal,xSep,xAft = xValue.partition('#')
            childrenList.append(xAft)
        return childrenList
    
    
    
    def loadFreeSurferNames(self,filename,structure):
        """Function that uses urllib/urllib2 to issue a SPARQL query.
           By default it requests json as data format for the SPARQL resultset"""
        f='application/json'
        data= open(filename, 'r').read()
        data=data.replace('FREENAME', structure)
        apikey = "73f776e6-e21b-4bce-8420-24f9a3670dbb"
        sparql_service = "http://sparql.bioontology.org/sparql/"
        try:
            params = {'query': data, 
                      'apikey': apikey,
     #                 'csrfmiddlewaretoken' : '8e241a744d2b70806cb21189cb1b0744'
                     }
            params = urllib.urlencode(params)
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            request = urllib2.Request(sparql_service+'?'+params)
            request.add_header('Accept', f)
            request.get_method = lambda: 'GET'
            url = opener.open(request)
            json_string= url.read()
        except Exception, e:
            traceback.print_exc(file=sys.stdout)
            raise e
        resultset=json.loads(json_string)
        print resultset
        miLista = resultset['results']['bindings']
        print miLista
        for miItem in miLista:
            xValue = miItem['codes']['value']
            xVal,xSep,xAft = xValue.partition('#')
            yValue = miItem['names']['value']
            print xAft  + '\t' + yValue
            
    def loadPre_FreeNames(self,filename):
        """Function that uses urllib/urllib2 to issue a SPARQL query.
           By default it requests json as data format for the SPARQL resultset"""
        f='application/json'
        data= open(filename, 'r').read()
        apikey = "73f776e6-e21b-4bce-8420-24f9a3670dbb"
        sparql_service = "http://sparql.bioontology.org/sparql/"
        try:
            params = {'query': data, 
                      'apikey': apikey,
     #                 'csrfmiddlewaretoken' : '8e241a744d2b70806cb21189cb1b0744'
                     }
            params = urllib.urlencode(params)
            opener = urllib2.build_opener(urllib2.HTTPHandler)
            request = urllib2.Request(sparql_service+'?'+params)
            request.add_header('Accept', f)
            request.get_method = lambda: 'GET'
            url = opener.open(request)
            json_string= url.read()
        except Exception, e:
            traceback.print_exc(file=sys.stdout)
            raise e
        resultset=json.loads(json_string)
        print resultset
        miLista = resultset['results']['bindings']
        print miLista
        names = list()
        for miItem in miLista:
            xValue = miItem['codes']['value']
            xVal,xSep,xAft = xValue.partition('#')
            yValue = miItem['PreferredNames']['value']
            zValue = miItem['freeSurfer']['value']
            names.append(xAft  + '\t' + yValue + '\t' + zValue +'\n')
        myfile=open('File\\rdfqueries\\FreeNames','w')
        myfile.writelines(names)

        
myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
#myManager.loadRdf('File\\RDFFiles\\Cascaron.ttl') ##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
#myManager.loadRdf('File\\RDFFiles\\JerarquiasComp.ttl')##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
#myManager.loadQuery('C:\Users\jc.forero47\Documents\JohanaForero\Repositorios\\braviz\\braint\java\\braint_v_1.0\File\\rdfqueries\EvaluationIdTestIdSubtestIdSubSubTest') #Lanza una query que entra como parametro en el archi ve entrada
#myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','CLINI', 'hasSubTest' )
#myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','FSIQ', 'isRelatedWith' )
#myManager.loadFreeSurferNames('File\\rdfqueries\\StructureNames','G_frontal_inf-Orbital_part')
#myManager.loadPre_FreeNames('File\\rdfqueries\\PreferredFreeCodeNames')