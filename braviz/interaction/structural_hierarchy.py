"""Creating hierarchies from free surfer names"""
import braviz
from braviz.utilities import recursive_default_dict
__author__ = 'Diego'



def get_structural_hierarchy(reader,subj):
    """
    returns a dictionary with a hierarchy from free surfer structures read from reader

    The hierarchy contains multiples copies of each structure, for different search options the top levels are:
    Right Hemisphere : Gray and white matter
    Left Hemisphere : Gray and white matter
    Dominant Hemisphere : Gray and white matter
    Nondominant Hemisphere : Gray and white matter
    Corpus Callosum : Gray and white matter
    Base (Subcortical structures)
    Fibers (named fibers)
    """
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
        if fib.endswith('_r'):
            #dominant and non dominant
            hierarchy_dict['Fibers'][fib[:-1]+'d']
            hierarchy_dict['Fibers'][fib[:-1] + 'n']
    return hierarchy_dict


if __name__=='__main__':
    reader2=braviz.readAndFilter.kmc40AutoReader()
    hier=get_structural_hierarchy(reader2,'144')
    print hier
