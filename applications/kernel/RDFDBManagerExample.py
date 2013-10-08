import urllib
import httplib2

#Conexion al repositorio sesame-rdf donde se suben los archivos turtle cascaron y jerarquias!
repository = 'pythonBD'
graph      = '<http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53>'
filename   = 'C:\Users\jc.forero47\Dropbox\TesisMe\Cascaron.ttl'
print "Loading %s into %s in Sesame" % (filename, graph)
params = { 'context': '<' + graph + '>' }
endpoint = "http://localhost:8080/openrdf-sesame/repositories/%s/statements?%s" % (repository, urllib.urlencode(params))
data = open(filename, 'r').read()
(response, content) = httplib2.Http().request(endpoint, 'PUT', body=data, headers={ 'content-type': 'text/turtle' })
print "Response %s" % response.status
print content

repository = 'pythonBD'
graph      = '<http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53>'
filename   = 'C:\Users\jc.forero47\Dropbox\TesisMe\ArchivosRDF\JerarquiasCom .ttl'
print "Loading into in Sesame %s" % filename
params = { 'context': '<' + graph + '>' }
endpoint = "http://localhost:8080/openrdf-sesame/repositories/%s/statements?%s" % (repository, urllib.urlencode(params))
data = open(filename, 'r').read()
(response, content) = httplib2.Http().request(endpoint, 'PUT', body=data, headers={ 'content-type': 'text/turtle' })
print "Response %s" % response.status
print content

