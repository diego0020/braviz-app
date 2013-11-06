import braviz
from braviz.utilities import recursive_default_dict
__author__ = 'Diego'



def get_structural_hierarchy(reader,subj):
    structure_names=reader.get('model',subj,index=True)
    hierarchy_dict=recursive_default_dict()
    for struct in structure_names:
        if struct.startswith('ctx-'):
            hemisphere= 'Right Hemisphere' if struct[4]=='r' else 'Left Hemisphere'
            name=struct[7:]
            hierarchy_dict[hemisphere][name]['Gray Matter']
        elif struct.startswith('wm-'):
            hemisphere = 'Right Hemisphere' if struct[3] == 'r' else 'Left Hemisphere'
            name = struct[6:]
            hierarchy_dict[hemisphere][name]['White Matter']
        elif struct.startswith('CC'):
            name=struct[3:]
            hierarchy_dict['Corpus Callosum'][name]
        else:
            hierarchy_dict['Base'][struct]
    named_fibers=reader.get('fibers',subj,index=True)
    for fib in named_fibers:
        hierarchy_dict['Fibers'][fib]
    return hierarchy_dict


if __name__=='__main__':
    reader=braviz.readAndFilter.kmc40AutoReader()
    hier=get_structural_hierarchy(reader,'144')
    print hier
