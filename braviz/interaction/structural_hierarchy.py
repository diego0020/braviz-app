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
            hierarchy_dict[hemisphere]['All Gray Matter'][name]
            hierarchy_dict['Dominant Hemisphere']['All Gray Matter'][name]
            hierarchy_dict['Nondominant Hemisphere']['All Gray Matter'][name]
            hierarchy_dict['Dominant Hemisphere'][name]['Gray Matter']
            hierarchy_dict['Nondominant Hemisphere'][name]['Gray Matter']
        elif struct.startswith('wm-'):
            hemisphere = 'Right Hemisphere' if struct[3] == 'r' else 'Left Hemisphere'
            name = struct[6:]
            hierarchy_dict[hemisphere][name]['White Matter']
            hierarchy_dict[hemisphere]['All White Matter'][name]
            hierarchy_dict['Dominant Hemisphere']['All White Matter'][name]
            hierarchy_dict['Nondominant Hemisphere']['All White Matter'][name]
            hierarchy_dict['Dominant Hemisphere'][name]['White Matter']
            hierarchy_dict['Nondominant Hemisphere'][name]['White Matter']
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
