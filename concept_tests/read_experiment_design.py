__author__ = 'Diego'

import os
import numpy as np
import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib import pyplot as plt
import seaborn as sns
from itertools import izip


#os.chdir(r"C:\Users\Diego\Documents\kmc400\spm\119\ATENCIONSENSE\FirstLevel")
os.chdir(r"C:\Users\Diego\Documents\kmc400\spm\119\MIEDOSofToneSENSE\FirstLevel")
#os.chdir(r"C:\Users\Diego\Documents\kmc400\spm\119\COORDINACIONSENSE\FirstLevel")
from scipy import io as sio
spm_mat = sio.matlab.loadmat("SPM.mat")

spm = spm_mat["SPM"]

TR = spm["xY"][0,0]["RT"][0,0][0,0]
units = spm["xBF"][0,0]["UNITS"][0,0][0]
time_bin= spm["xBF"][0,0]["dt"][0,0][0,0]
tr_divisions = spm["xBF"][0,0]["T"][0,0][0,0]
n_scans = spm["nscan"][0,0][0,0]

print "TR = ",TR
print units
print time_bin
print n_scans

time_vec = np.arange(0,TR*n_scans,time_bin)

session = spm["Sess"][0,0]
covar_names = [x[0] for x in session["C"][0,0]["name"][0,0][0,:] ]
plt.hold(True)
n_conds = session["U"][0,0].shape[1]
color_cycle = sns.color_palette("Dark2", n_conds)
for i in xrange(n_conds):
    condition = np.zeros(time_vec.shape)
    session_info = session["U"][0, 0][0, i]
    cond_name = session_info["name"][0,0][0]
    cond_onsets = session_info["ons"][:,0].astype(np.int)
    cond_durations = session_info["dur"][:,0]
    cond_time_bin= session_info["dt"][0,0]
    print "%s : %s,%s (%s)"%(cond_name,cond_onsets,cond_durations,cond_time_bin)
    for onset,duration in izip(cond_onsets,cond_durations):
        onset_d = onset*tr_divisions if units == "scans" else int(onset/time_bin)
        dur_d = duration*tr_divisions if units == "scans" else int(duration/time_bin)
        condition[onset_d:onset_d+dur_d]=1
    c = color_cycle[i]
    plt.plot(time_vec,condition,label=cond_name,c=c)
    plt.fill_between(time_vec,condition,alpha=0.5,color=c)

plt.legend()
plt.ylim(-0.5,1.5)
plt.show()




