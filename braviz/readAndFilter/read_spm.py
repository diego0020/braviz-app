from __future__ import division
from scipy import io as sio

__author__ = 'Diego'

def get_contrasts_dict(spm_file_path):
    spm_file = sio.loadmat(spm_file_path)
    spm_struct = spm_file["SPM"][0,0]
    contrasts_info = spm_struct["xCon"]
    n_contrasts = contrasts_info.shape[1]
    contrast_names = {}
    for i in xrange(n_contrasts):
        contrast_names[i+1] = contrasts_info[0,i]["name"][0]
    return contrast_names
