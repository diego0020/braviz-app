__author__ = 'Diego'

import braviz
import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib import pyplot as plt
import numpy as np
import seaborn as sbn

reader = braviz.readAndFilter.BravizAutoReader()
ids = reader.get("ids")
fmris = {}

x,y,z = 30,18,18
def get_data():
    for i in ids:
        try:
            fmris[i] = reader.get("bold",i,name="PRECISION").get_data()[x,y,z,:]
        except Exception:
            pass
fmris.clear()
get_data()
ls = [len(x) for x in fmris.values()]
print ls
sbn.tsplot(fmris.values(),range(80))

plt.show()
sbn.tsplot(fmris.values(),range(80),err_style="unit_traces")
plt.show()
signals = fmris.values()
signals2=[s - np.mean(s) for s in signals]
sbn.tsplot(signals2,range(80),err_style="unit_traces")
plt.show()

signals3 = [s / np.std(s) for s in signals2 ]
sbn.tsplot(signals3,range(80),err_style="unit_traces")
plt.show()
sbn.tsplot(signals3,range(80))
plt.show()
sbn.tsplot(signals3,range(80),err_style="boot_traces")
plt.show()

sbn.tsplot(signals3,range(80),err_style="boot_kde")
plt.show()

