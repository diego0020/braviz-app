__author__ = 'Diego'

import logging
from itertools import izip

import pandas as pd
import pandas.rpy.common as com
import rpy2.rinterface
from rpy2 import robjects
from rpy2.robjects.packages import importr
import numpy as np

import braviz.readAndFilter.tabular_data as braviz_tab_data


def import_or_install(lib_name):
    try:
        lib=importr(lib_name)
    except rpy2.rinterface.RRuntimeError:
        print "please install %s from R"%lib_name
        log = logging.getLogger(__name__)
        log.error("Couldn't load R package %s",lib_name)
        raise
    return lib

def calculate_ginni_index(outcome,data_frame):
    #construct data frame
    is_nominal=False
    conn=braviz_tab_data.get_connection()
    res=conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(outcome,))
    outcome_idx = braviz_tab_data.get_var_idx(outcome)
    is_real=res.fetchone()
    if (is_real is not None) and is_real[0]==0:
        is_nominal=True

    values_data_frame=braviz_tab_data.get_data_frame_by_index(data_frame.index,col_name_index=True)
    #remove columns with many NaNs
    #df2=values_data_frame.dropna(1,thresh=40)
    values_data_frame.dropna(1,thresh=30,inplace=True)
    #df3=df2.dropna(0,thresh=200)
    values_data_frame.dropna(0,thresh=200,inplace=True)
    #fill nas with other values
    #shuffle
    permutation=np.random.permutation(range(len(values_data_frame)))
    values_data_frame=values_data_frame.iloc[permutation]
    values_data_frame.fillna(method="pad",inplace=True)
    values_data_frame=values_data_frame.iloc[reversed(permutation)]
    values_data_frame.fillna(method="pad",inplace=True)
    #just in case there are still nas
    values_data_frame.dropna(0,inplace=True)
    values_data_frame.dropna(1,inplace=True)
    #create R data frame
    original_column_names=values_data_frame.columns

    #More R friendly column names
    values_data_frame.columns=["c%s"%i for i in xrange(len(values_data_frame.columns))]

    r_df=com.convert_to_r_dataframe(values_data_frame)
    #if oucome is nominal transform into factor
    outcome_variable_index=original_column_names.get_loc(outcome_idx)
    r_environment=robjects.globalenv
    r_environment["r_df"]=r_df
    if is_nominal:

        robjects.r('r_df["c%d"] <- factor( r_df[["c%d"]])'%(outcome_variable_index,outcome_variable_index))


    r_df=r_environment["r_df"]

    #for i,n in enumerate(original_column_names):
    #    print "%d \t %s"%(i,n)
    #print r_df
    #import randomForest
    randomForest=import_or_install("randomForest")

    #use correct variable in formula
    form=robjects.Formula("c%d~."%outcome_variable_index)
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
    data_frame["Ginni"][outcome_idx]=np.inf
    #print self.data_frame
    return data_frame

def calculate_anova(outcome,regressors_data_frame,interactions_dict,sample):
    #is outcome nominal?
    is_nominal=braviz_tab_data.is_variable_name_nominal(outcome)

    #is outcome binary?
    is_binary=False
    if is_nominal:
        # res=conn.execute("SELECT count(*) FROM nom_meta NATURAL JOIN variables WHERE var_name = ?",(outcome,))
        # if res.fetchone()[0]==2:
        #     is_binary=True
        # else:
        #     is_binary=False
        log = logging.getLogger(__name__)
        log.error("Logistic and multinomial ANOVA not yet implemented, choose a real outcome")
        raise Exception("Logistic and multinomial ANOVA not yet implemented, choose a real outcome")

    #are regressors nominal?
    factors_nominal=dict()
    var_names=regressors_data_frame[regressors_data_frame["Interaction"]==0]["variable"].tolist()
    for var in var_names:
        factors_nominal[var]=braviz_tab_data.is_variable_name_nominal(var)
    #print factors_nominal

    #construct pandas data frame
    var_names.append(outcome)
    pandas_df=braviz_tab_data.get_data_frame_by_name(var_names)
    pandas_df=pandas_df.loc[sample]
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
    stats=import_or_install("stats")
    contrasts_dict={}
    for i,var in enumerate(var_names[:-1]):
        if factors_nominal[var]:
            k="r%d"%i
            contrasts_dict[k]=stats.contr_sum


    #run anova
    car=import_or_install("car")

    if len(contrasts_dict)>0:
        contrasts_list=robjects.ListVector(contrasts_dict)
        model=stats.lm(form,data=r_df,contrasts=contrasts_list)
    else:
        model=stats.lm(form,data=r_df)
    intercept=model[0][0]
    residuals=np.array(model[1])
    anova=car.Anova(model,type=3)
    fitted = np.array(model[4])
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

    return output_df,residuals,intercept,fitted

def calculate_normalized_linear_regression(outcome,regressors_data_frame,interactions_dict,sample):
    if not braviz_tab_data.is_variable_name_real(outcome):
        raise NotImplementedError("Logistic regression not yet implemented, please select a rational outcome")
    regressor_names=regressors_data_frame[regressors_data_frame["Interaction"]==0]["variable"].tolist()
    all_variables = [outcome]+regressor_names
    data_frame = braviz_tab_data.get_data_frame_by_name(all_variables)
    data_frame = data_frame.loc[sample].copy()
    data_frame.dropna(inplace=True)
    #we have to classify variables in real, binary, and other nominals
    var_type = dict()
    for var in regressor_names:
        if braviz_tab_data.is_variable_name_real(var):
            var_type[var]='r'
        else:
            #is it binary?
            levels = len(np.unique(data_frame[var]))
            if levels == 2:
                var_type[var]='b'
            else:
                var_type[var]='n'
    #for binary and real variables we need the mean, for real variables we also need the std_dev to de-standardize
    mean_sigma = dict()
    for var,t in var_type.iteritems():
        if t == "r":
            m = np.mean(data_frame[var])
            std = np.std(data_frame[var])
            mean_sigma[var] = (m,std)
        elif t == "b":
            m = np.mean(data_frame[var])
            # we are going to use center in arm.standardize:
            # "center" (rescale so that the mean of the data is 0 and the difference between the two categories is 1),
            # in the real case we divide by 2$\sigma$, so the final sd is 0.5
            std = 0.5
            mean_sigma[var] = (m,std)

    #variable names can be strange (unicode) ... we are going to change them to more abstract names like in anova
    standard_var_names = ["var_%d_R"%i for i in xrange(len(all_variables))]
    #now create a data frame with the new names
    data_frame_std = data_frame.copy()
    assert all(data_frame_std.columns == all_variables)
    data_frame_std.columns = standard_var_names

    #now we are ready to go into the R world
    r_data_frame = com.convert_to_r_dataframe(data_frame_std)
    # create factor variables
    r_environment=robjects.globalenv
    r_environment["r_df"]=r_data_frame
    for var,s_name in izip(all_variables,standard_var_names):
        t = var_type.get(var,"r")
        if t != "r":
            robjects.r('r_df["%s"] <- factor( r_df[["%s"]])'%(s_name,s_name))
    r_data_frame=r_environment["r_df"]
    #construct the formula
    coefficients = standard_var_names
    for products in interactions_dict.itervalues():
        factors=[]
        for f in products:
            f_name=regressors_data_frame["variable"][f]
            f_index=all_variables.index(f_name)
            std_name=standard_var_names[f_index]
            factors.append(std_name)
        coefficients.append("*".join(factors))
    formula_str = "var_0_R ~ "+"+".join(coefficients[1:])
    #calculate the linear model
    robjects.r("r_lm <- lm(%s,data=r_df)"%formula_str)
    #standardize
    robjects.r("library('arm')")
    robjects.r("s_lm_r <- standardize(r_lm)")
    standardized_model = r_environment["s_lm_r"]

    #now we have to extract the results
    print standardized_model
    r_coeffs = standardized_model.rx2("coefficients")
    coef_dict_std = dict(izip(r_coeffs.names,r_coeffs))
    residuals = list(standardized_model.rx2("residuals"))
    fitted = list(standardized_model.rx2("fitted.values"))

    intercept = coef_dict_std.pop("(Intercept)")
    coef_dicts = dict()
    for std_name,val in coef_dict_std.iteritems():
        if ":" in std_name:
            #interactions
            factors=std_name.split(":")
        else:
            factors = [std_name]
        orig_factors = []
        for f in factors:
            dummy_level = None
            if f[1] == ".":
                f = f[2:]
            if f[-1] != "R":
                r_pos = f.rfind("R")
                dummy_level = f[r_pos+1:]
                f = f[:r_pos+1]
            index = standard_var_names.index(f)
            orig_name = all_variables[index]
            if dummy_level is not None:
                orig_name+="_%s"%dummy_level
            orig_factors.append(orig_name)
        if len(orig_factors) == 1:
            coef_dicts[orig_factors[0]]=val
        else:
            coef_dicts[frozenset(orig_factors)]=val

    #print coef_dicts
    #recover original names in the coef_dict
    out_dict = {
        "coefficients" : coef_dicts,
        "residuals" : residuals,
        "fitted" : fitted,
        "intercept" : intercept,
    }
    return out_dict