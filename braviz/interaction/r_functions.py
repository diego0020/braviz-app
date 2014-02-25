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

def is_variable_nominal(variable):
    is_nominal=False

    conn=braviz_tab_data.get_connection()
    res=conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(variable,))
    is_real=res.fetchone()
    if (is_real is not None) and is_real[0]==0:
        is_nominal=True
    conn.close()
    return is_nominal

def is_variable_real(variable):
    return not is_variable_nominal(variable)

def calculate_anova(outcome,regressors_data_frame,interactions_dict):
    #is outcome nominal?
    is_nominal=is_variable_nominal(outcome)

    #is outcome binary?
    conn=braviz_tab_data.get_connection()
    is_binary=False
    if is_nominal:
        res=conn.execute("SELECT count(*) FROM nom_meta NATURAL JOIN variables WHERE var_name = ?",(outcome,))
        if res.fetchone()[0]==2:
            is_binary=True
        else:
            is_binary=False
        raise Exception("Logistic and multinomial ANOVA not yet implemented, choose a real outcome")

    #are regressors nominal?
    factors_nominal=dict()
    var_names=regressors_data_frame[regressors_data_frame["Interaction"]==0]["variable"].tolist()
    for var in var_names:
        factors_nominal[var]=is_variable_nominal(var)
    #print factors_nominal

    #construct pandas data frame
    var_names.append(outcome)
    pandas_df=braviz_tab_data.get_data_frame(var_names)
    #print pandas_df

    #construct r data frame

    new_names=["r%d"%i for i in xrange(len(var_names))]
    new_names[-1]="o"

    pandas_df.columns=new_names
    r_df=com.convert_to_r_dataframe(pandas_df)
    #print r_df

    #reformat r_df
    r_environment=robjects.globalenv
    r_environment["r_df"]=r_df
    for i,var in enumerate(var_names):
        if factors_nominal.get(var,False):
            robjects.r('r_df["r%d"] <- factor( r_df[["r%d"]])'%(i,i))

    r_df=r_environment["r_df"]
    #print r_df
    #construct formula
    regressors=new_names[:-1]
    interactions=[]
    #print interactions_dict
    for products in interactions_dict.itervalues():
        factors=[]
        for f in products:
            f_name=regressors_data_frame["variable"][f]
            f_index=var_names.index(f_name)
            f_new_name=new_names[f_index]
            factors.append(f_new_name)
        interactions.append("*".join(factors))

    regressors.extend(interactions)
    formula_str="o~"+"+".join(regressors)
    #print formula_str
    form=robjects.Formula(formula_str)

    #construct constrasts list
    stats=importr("stats")
    contrasts_dict={}
    for i,var in enumerate(var_names[:-1]):
        if factors_nominal[var]:
            k="r%d"%i
            contrasts_dict[k]=stats.contr_sum

    contrasts_list=robjects.ListVector(contrasts_dict)
    #run anova
    car=importr("car")
    model=stats.lm(form,data=r_df,contrasts=contrasts_list)
    intercept=model[0][0]
    residuals=np.array(model[1])
    anova=car.Anova(model,type=3)
    #print anova
    # print "Intercept "+' '.join(regressors)+" Residuals"
    # print "sum of squares:"
    # print anova[0]
    # print "DF:"
    # print anova[1]
    # print "F-value"
    # print anova[2]
    # print "P-value"
    # print anova[3]

    #create output data_frame

    # sum_sq=list(anova.rx(True,1))
    # r_dfs=list(anova.rx(True,2))
    # f_values=list(anova.rx(True,3))
    # p_values=list(anova.rx(True,4))

    row_names=list(anova.rownames)
    column_names=list(anova.names)

    output_dict=dict( (k,list(anova.rx(True,i+1))) for i,k in enumerate(column_names))

    #decode column_names
    def decode_colum_names(name):
        tokens=name.split(":")
        fs=[]
        for t in tokens:
            try:
                i=new_names.index(t)
            except ValueError:
                f=t
            else:
                f=var_names[i]
            fs.append(f)
        return ":".join(fs)

    decoded_names=map(decode_colum_names,row_names)

    output_df=pd.DataFrame(output_dict,index=decoded_names)

    #reorder to match r order
    output_df["Factor"]=output_df.index
    output_df=output_df[["Factor","Sum Sq","Df","F value","Pr(>F)"]]


    return (output_df,residuals,intercept)

