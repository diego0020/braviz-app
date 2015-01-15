##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


__author__ = 'Diego'

long_messages_dict = {
    'Motor Brain': 'Tms tests',
    'Excitability': 'Basic level = 100% - motor threshold',
    'Synchronization': 'Corticospinal efficiency, msec',
    'Balanced Activity': 'Balance between inhibition and facilitation mechanisms',
    'Level of Inhibition': 'GABAa synapses = 100% - cond*100/test',
    'Level of Facilitation': 'Glutamate synapses = cond*100/test - 100%',
    'Cooperation between hemispheres': 'Integrity of corpus callosum = test of inhibition from the other hemisphere',
    'Frequency': 'Frequency of observation of an inhibition triggered by the other hemisphere',
    'Transfer time': 'Time for the transfer of the inhibition triggered by the other hemisphere',
    'Duration': 'Duration of the inhibition triggered by the other hemisphere',
}


data_codes_dict = {
    'Level of Inhibition': 'ICI',
    'Level of Facilitation': 'ICF',
    'Transfer time': 'IHIlat',
    'Duration': 'IHIdur',
    'Excitability': 'RMT',
    'Synchronization': 'MEPlat',
    'Frequency': 'IHIfreq'
}

hierarchy={
    'Motor Brain' : {
        'Excitability' : {},
        'Synchronization' : {},
        'Balanced Activity' :{
            'Level of Inhibition':{},
            'Level of Facilitation' : {},
        },
        'Cooperation between hemispheres':{
            'Frequency':{},
            'Transfer time':{},
            'Duration':{},
        }
    }
}

hierarchy_dnd={
    'Motor Brain' : {
        'Excitability' : {'Dominant' : {}, 'Nondominant': {}},
        'Synchronization' : {'Dominant' : {}, 'Nondominant': {}},
        'Balanced Activity' :{
            'Level of Inhibition':{'Dominant' : {}, 'Nondominant': {}},
            'Level of Facilitation' : {'Dominant' : {}, 'Nondominant': {}},
        },
        'Cooperation between hemispheres':{
            'Frequency':{'Dominant' : {}, 'Nondominant': {}},
            'Transfer time':{'Dominant' : {}, 'Nondominant': {}},
            'Duration':{'Dominant' : {}, 'Nondominant': {}},
        }
    }
}