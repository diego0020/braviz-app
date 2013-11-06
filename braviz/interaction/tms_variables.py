__author__ = 'Diego'

long_messages_dict = {
    'motor_brain': 'Tms tests',
    'Excitability': 'Basic level = 100% - motor threshold',
    'Synchronization': 'Corticospinal efficiency, msec',
    'balan': 'Balance between inhibition and facilitation mechanisms',
    'Level of Inhibition': 'GABAa synapses = 100% - cond*100/test',
    'Level of Facilitation': 'Glutamate synapses = cond*100/test - 100%',
    'coop': 'Integrity of corpus callosum = test of inhibition from the other hemisphere',
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