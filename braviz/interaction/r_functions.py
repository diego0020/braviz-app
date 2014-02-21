__author__ = 'Diego'

import braviz.readAndFilter.tabular_data as braviz_tab_data
import pandas as pd
import pandas.rpy.common as com
from rpy2 import robjects
from rpy2.robjects.packages import importr
import numpy as np



def calculate_ginni_index(outcome,data_frame):
    #construct data frame
    is_nominal=False
    conn=braviz_tab_data.get_connection()
    res=conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(outcome,))
    is_real=res.fetchone()
    if (is_real is not None) and is_real[0]==0:
        is_nominal=True

    values_data_frame=braviz_tab_data.get_data_frame(data_frame["var_name"])
    #remove columns with many NaNs
    #df2=values_data_frame.dropna(1,thresh=40)
    values_data_frame.dropna(1,thresh=40,inplace=True)
    #df3=df2.dropna(0,thresh=200)
    values_data_frame.dropna(0,thresh=200,inplace=True)
    #fill nas with other values
    #shuffle
    permutation=np.random.permutation(range(len(values_data_frame)))
    values_data_frame=values_data_frame.iloc[permutation]
    values_data_frame.fillna(method="pad",inplace=True)
    values_data_frame=values_data_frame.iloc[reversed(permutation)]
    values_data_frame.fillna(method="pad",inplace=True)
    #create R data frame
    original_column_names=values_data_frame.columns

    #More R friendly column names
    values_data_frame.columns=["c%s"%i for i in xrange(len(values_data_frame.columns))]

    r_df=com.convert_to_r_dataframe(values_data_frame)
    #if oucome is nominal transform into factor
    outcome_variable_index=original_column_names.get_loc(outcome)
    if is_nominal:
        r_environment=robjects.globalenv
        r_environment["r_df"]=r_df
        robjects.r('r_df["c%d"] <- factor( r_df[["c%d"]])'%(outcome_variable_index,outcome_variable_index))
        r_df=r_environment["r_df"]

    #for i,n in enumerate(original_column_names):
    #    print "%d \t %s"%(i,n)
    #print r_df
    #import randomForest
    randomForest=importr("randomForest")
    #use correct variable in formula
    form=robjects.Formula("c%d~."%outcome_variable_index)
    #robjects.globalenv["r_df"]=r_df
    #robjects.r("table(complete.cases(r_df))")

    fit=randomForest.randomForest(form,data=r_df,replace=True,importance=True)
    #fit=robjects.r("randomForest.randomForest(c6~.,data=r_df,replace=True,importance=True)")
    imp=fit.rx2("importance")
    #if outcome is factor it is different
    #print imp
    interesting_column_index=2
    if is_nominal:
        interesting_column_index=len(set(values_data_frame["c%d"%outcome_variable_index]))+2

    #extract column vector
    imp_v=np.zeros(imp.nrow)
    for i in xrange(imp.nrow):
        imp_v[i]=imp.rx(i+1,interesting_column_index)[0]

    #Remove target variable from original_names
    potential_regressors=list(original_column_names)
    potential_regressors.pop(outcome_variable_index)
    imp_data_frame=pd.DataFrame(imp_v,index=potential_regressors)
    #print imp_data_frame
    data_frame["Ginni"]=imp_data_frame
    data_frame.replace(np.nan,0,inplace=True)
    data_frame["Ginni"][outcome]=np.inf
    #print self.data_frame
    return data_frame


def calculate_anova():
    pass
