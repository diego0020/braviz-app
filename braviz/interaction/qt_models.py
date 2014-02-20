__author__ = 'Diego'
import pandas as pd
import numpy as np
import PyQt4.QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractListModel
from PyQt4.QtCore import QAbstractTableModel
import braviz.readAndFilter.tabular_data as braviz_tab_data
import pandas.rpy.common as com
from rpy2 import robjects
from rpy2.robjects.packages import importr



class VarListModel(QAbstractListModel):
    def __init__(self,outcome_var=None, parent=None):
        QAbstractListModel.__init__(self,parent)
        self.internal_data=[]
        self.header="Variable"
        self.update_list()
        self.outcome=outcome_var
    def update_list(self):
        panda_data=braviz_tab_data.get_variables()
        self.internal_data=list(panda_data["var_name"])
    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.internal_data)
    def data(self, QModelIndex, int_role=None):
        idx=QModelIndex.row()
        if 0 <= idx < len(self.internal_data) and int_role==QtCore.Qt.DisplayRole:
            return self.internal_data[idx]
        else:
            return QtCore.QVariant()
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if Qt_Orientation==QtCore.Qt.Horizontal and p_int==0:
            return self.header
        else:
            return QtCore.QVariant()
    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        self.internal_data.sort(reverse=reverse)
        self.modelReset.emit()

class VarAndGiniModel(QAbstractTableModel):
    def __init__(self,outcome_var=None,parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.data_frame=braviz_tab_data.get_variables()
        self.data_frame.index=self.data_frame["var_name"]
        self.data_frame["Ginni"]="?"
        self.ginni_calculated=False
        self.outcome=outcome_var

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2
    def data(self, QModelIndex, int_role=None):
        if not (int_role==QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line=QModelIndex.row()
        col=QModelIndex.column()
        if 0<=line<len(self.data_frame):
            if col==0:
                return self.data_frame["var_name"][line]
            elif col==1:
                return str(self.data_frame["Ginni"][line])
            else:
                return QtCore.QVariant()
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            if p_int==0:
                return "Variable"
            elif p_int==1:
                return "Importance"
        elif int_role == QtCore.Qt.ToolTipRole:
            if p_int==0:
                return "Variable name"
            elif p_int==1:
                return "This measure is calculated as how effective each variable is at predicting the outcome"
        else:
                return QtCore.QVariant()
    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        if p_int==0:
            self.data_frame.sort("var_name",ascending=reverse,inplace=True)
        elif p_int==1:
            if self.ginni_calculated is False:
                self.calculate_gini_indexes()
                self.ginni_calculated = True
            self.data_frame.sort("Ginni",ascending=reverse,inplace=True)
        self.modelReset.emit()

    def calculate_gini_indexes(self):
        #get outcome var:
        if self.outcome is None:
            print "An outcome var is required for this"
            return
        #construct data frame
        is_nominal=False
        conn=braviz_tab_data.get_connection()
        res=conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(self.outcome,))
        is_real=res.fetchone()
        if (is_real is not None) and is_real[0]==0:
            is_nominal=True

        values_data_frame=braviz_tab_data.get_data_frame(self.data_frame["var_name"])
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
        outcome_variable_index=original_column_names.get_loc(self.outcome)
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
        self.data_frame["Ginni"]=imp_data_frame
        self.data_frame.replace(np.nan,0,inplace=True)
        self.data_frame["Ginni"][self.outcome]=np.inf
        #print self.data_frame



class AnovaRegressorsModel(QAbstractTableModel):
    def __init__(self,regressors_list=tuple(),parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.conn=braviz_tab_data.get_connection()
        if len(regressors_list)>0:
            initial_data=( (r,self.get_degrees_of_freedom(r)) for r in regressors_list )
        else:
            initial_data=None
        self.data_frame=pd.DataFrame(initial_data,columns=["variable","DF"])


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            if p_int==0:
                return "Variable"
            elif p_int==1:
                return "DF"
        elif int_role==QtCore.Qt.ToolTipRole and p_int==1:
            return "Degrees of freedom"
        else:
            return  QtCore.QVariant()
    def data(self, QModelIndex, int_role=None):
        if not (int_role==QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line=QModelIndex.row()
        col=QModelIndex.column()
        if 0<=line<len(self.data_frame):
            if col==0:
                return self.data_frame["variable"].iloc[line]
            elif col==1:
                return str(self.data_frame["DF"].iloc[line])
            else:
                return QtCore.QVariant()
    def sort(self, p_int, Qt_SortOrder_order=None):
        #We will be using type2 or type3 Sums of Squares, and therefore order is not important
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        if p_int==0:
            self.data_frame.sort("variable",ascending=reverse,inplace=True)
        elif p_int==1:
            self.data_frame.sort("DF",ascending=reverse,inplace=True)
        self.modelReset.emit()
    def add_regressor(self,var_name):
        if (self.data_frame["variable"]==var_name).sum()>0:
            #ignore duplicates
            return

        self.beginInsertRows(QtCore.QModelIndex(),len(self.data_frame),len(self.data_frame))
        self.data_frame=self.data_frame.append(pd.DataFrame([(var_name,self.get_degrees_of_freedom(var_name) ) ],
                                                            columns=["variable","DF"], index=(len(self.data_frame),)
                                                            ))
        self.endInsertRows()

    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        self.beginRemoveRows(QtCore.QModelIndex(),row,row+count-1)
        indexes=list(self.data_frame.index)
        for i in xrange(count):
            indexes.pop(row)
        self.data_frame=self.data_frame.iloc[indexes]
        self.endRemoveRows()

    def get_degrees_of_freedom(self,var_name):
        is_real_cur=self.conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(var_name,))
        is_real=is_real_cur.fetchone()[0]
        if is_real is None or is_real == 1:
            return 1
        query="""SELECT count(*) FROM nom_meta NATURAL JOIN variables WHERE  var_name=?"""
        cur=self.conn.execute(query,(var_name,))
        return cur.fetchone()[0]



class NominalVariablesMeta(QAbstractTableModel):
    def __init__(self,var_name,parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.var_name=var_name
        self.conn=braviz_tab_data.get_connection()
        self.names_dict={}
        self.labels_list=[]
        self.headers=("label","name")
        self.update_model(var_name)
    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.names_dict)
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2
    def data(self, QModelIndex, int_role=None):
        if not (int_role==QtCore.Qt.DisplayRole or int_role == QtCore.Qt.EditRole):
            return QtCore.QVariant()
        line=QModelIndex.row()
        col=QModelIndex.column()
        if 0<=line<len(self.labels_list):
            if col==0:
                return self.labels_list[line]
            elif col==1:
                return self.names_dict[self.labels_list[line]]
            else:
                return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if Qt_Orientation==QtCore.Qt.Horizontal:
            if p_int==0:
                return "Label"
            elif p_int==1:
                return "Name"
        else:
            return QtCore.QVariant()
    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        self.labels_list.sort(reverse=reverse)
        self.modelReset.emit()
    def setData(self, QModelIndex, QVariant, int_role=None):
        row=QModelIndex.row()
        col=QModelIndex.column()
        #print "Data change requested"
        #print int_role
        #print QVariant
        if int_role != QtCore.Qt.EditRole:
            return False
        if col != 1 or row <0 or row >= self.rowCount():
            return False
        self.names_dict[self.labels_list[row]]=unicode(QVariant.toString())
        self.dataChanged.emit(QModelIndex,QModelIndex)
        return True


    def flags(self, QModelIndex):
        row=QModelIndex.row()
        col=QModelIndex.column()
        flags=QtCore.Qt.NoItemFlags
        if 0<=row<self.rowCount() and 0<=col<self.columnCount():
            flags=flags | QtCore.Qt.ItemIsSelectable
            flags=flags | QtCore.Qt.ItemIsEnabled
            if col==1:
                flags=flags | QtCore.Qt.ItemIsEditable
        return flags

    def update_model(self,var_name):
        #print "*****loading model"
        self.var_name=var_name
        cur=self.conn.cursor()
        #Get labels
        query="""
        SELECT label2, name
        from
        (
        SELECT  distinct value as label2, variables.var_idx as var_idx2
        FROM variables natural join var_values
        WHERE variables.var_name = ?
        ) left outer join
        nom_meta ON (nom_meta.label = label2 and var_idx2 = nom_meta.var_idx)
        ORDER BY label2;
        """
        cur.execute(query,(self.var_name,))
        labels=cur.fetchall()
        self.names_dict=dict(labels)
        self.labels_list=list(self.names_dict.iterkeys())
    def save_into_db(self):
        #print self.names_dict
        query="""INSERT OR REPLACE INTO nom_meta
        VALUES (
        (SELECT var_idx FROM variables WHERE var_name = ?),
        ?, -- label
        ? -- name
        );
        """
        tuples=( (self.var_name, k, v) for k,v in self.names_dict.iteritems())
        self.conn.executemany(query,tuples)
        self.conn.commit()