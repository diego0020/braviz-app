'''
Created on 26/10/2013

@author: jc.forero47
'''

list_volumes = open('File\\rdfqueries\\VolumesNames').readlines()
list_rdf_codes = open('File\\rdfqueries\\FreeNames').readlines()

triplet_file = open('File\\RDFFiles\\volumesTriplets.ttl', 'w')

radlex_codes = list()
for volume in list_volumes:
    for rdf_code in list_rdf_codes:
        raw_code = rdf_code.split('#')
        freesurfer_name = raw_code[2].strip()
        volume = volume.strip()
        if raw_code[0] not in radlex_codes: 
            if  freesurfer_name == volume:
                triplet_file.write(':%s rdf:type braint:SubSubTest,\n'%raw_code[0])
                triplet_file.write('\t\t\towl:NamedIndividual ;\n')
                triplet_file.write('\t\t\tbraint:SubSubtest_Name "volume of %s" ;\n'%raw_code[1])
                triplet_file.write('\t\t\tbraint:Freesurfer_Name "%s" ;\n'%freesurfer_name)
                triplet_file.write('\t\t\tbraint:SubSubTest_DataType "Ordinal" ;\n')
                triplet_file.write('\t\t\tbraint:SubSubtest_Description "missing... Measure from Freesurfer" ;\n')
                triplet_file.write('\t\t\tbraint:hasVisualization :a ;\n')
                triplet_file.write('\t\t\tbraint:isRelatedWith :b ;\n')
                triplet_file.write('\t\t\tbraint:isMentionedIn :c .\n\n\n')
                radlex_codes.append(raw_code[0])

triplet_file.write(':VOLUM rdf:type braint:SubTest ,\n')
triplet_file.write('\t\t\towl:NamedIndividual ;\n')
triplet_file.write('\t\t\tbraint:SubTest_Name "Volume" ;\n')
triplet_file.write('\t\t\tbraint:SubTest_DataType "Ordinal" ;\n')
triplet_file.write('\t\t\tbraint:SubTest_Description "missing" ;\n')
triplet_file.write('\t\t\tbraint:hasVisualization :JAVI1 ;\n')
triplet_file.write('\t\t\tbraint:hasSubSubTest :%s,\n'%radlex_codes[0])

for i in  range(1, len(radlex_codes) - 1):
    triplet_file.write('\t\t\t\t\t\t\t\t:%s ,\n'%radlex_codes[i])
triplet_file.write('\t\t\t\t\t\t\t\t:%s .\n'%radlex_codes[-1])
print 'End creating ttl file'

