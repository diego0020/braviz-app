__author__ = 'Diego'
import pandas as pd
import numpy as np
import PyQt4.QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractListModel
from PyQt4.QtCore import QAbstractTableModel, QAbstractItemModel
import braviz.readAndFilter.tabular_data as braviz_tab_data
from braviz.interaction.r_functions import calculate_ginni_index,calculate_anova



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
        self.data_frame=calculate_ginni_index(self.outcome,self.data_frame)



class AnovaRegressorsModel(QAbstractTableModel):
    def __init__(self,regressors_list=tuple(),parent=None):
        QAbstractTableModel.__init__(self,parent)
        self.conn=braviz_tab_data.get_connection()
        if len(regressors_list)>0:
            initial_data=( (r,self.get_degrees_of_freedom(r),0) for r in regressors_list )
        else:
            initial_data=None
        self.data_frame=pd.DataFrame(initial_data,columns=["variable","DF","Interaction"])
        self.display_view=self.data_frame
        self.__show_interactions=True
        self.__show_regressors=True
        self.__interactors_dict=dict()
        self.__next_index=0


    def update_display_view(self):
        if (self.__show_interactions and self.__show_regressors):
            self.display_view=self.data_frame
        else:
            if self.__show_interactions is True:
                self.display_view=self.data_frame[self.data_frame["Interaction"]==1]
            else:
                self.display_view=self.data_frame[self.data_frame["Interaction"]==0]


    def show_interactions(self,value=True):
        self.__show_interactions=value
        self.update_display_view()
        self.modelReset.emit()

    def show_regressors(self,value=True):
        self.__show_regressors=value
        self.update_display_view()
        self.modelReset.emit()


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.display_view)

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
        line=QModelIndex.row()
        col=QModelIndex.column()
        if not (int_role==QtCore.Qt.DisplayRole):
            return QtCore.QVariant()


        if 0<=line<self.rowCount():
            if col==0:
                return self.display_view["variable"].iloc[line]
            elif col==1:
                return str(self.display_view["DF"].iloc[line])
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
        self.update_display_view()
        self.modelReset.emit()
    def add_regressor(self,var_name):
        if (self.data_frame["variable"]==var_name).sum()>0:
            #ignore duplicates
            return

        self.beginInsertRows(QtCore.QModelIndex(),len(self.data_frame),len(self.data_frame))
        self.data_frame=self.data_frame.append(pd.DataFrame([(var_name,self.get_degrees_of_freedom(var_name),0 ) ],
                                                            columns=["variable","DF","Interaction"],
                                                            index=(self.__next_index,)
                                                            ))
        self.__next_index+=1
        self.endInsertRows()
        self.update_display_view()

    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        #self.layoutAboutToBeChanged.emit()
        self.beginRemoveRows(QtCore.QModelIndex(),row,row+count-1)
        indexes=list(self.data_frame.index)
        for i in xrange(count):
            indexes.pop(row)
        if len(indexes)==0:
            self.data_frame=pd.DataFrame(columns=["variable","DF","Interaction"])
        else:
            print self.data_frame
            print indexes
            self.data_frame=self.data_frame.loc[indexes]


        self.remove_invalid_interactions()
        self.update_display_view()
        self.endRemoveRows()
        self.modelReset.emit()


    def get_degrees_of_freedom(self,var_name):
        is_real_cur=self.conn.execute("SELECT is_real FROM variables WHERE var_name = ?",(var_name,))
        is_real=is_real_cur.fetchone()[0]
        if is_real is None or is_real == 1:
            return 1
        query="""SELECT count(*) FROM nom_meta NATURAL JOIN variables WHERE  var_name=?"""
        cur=self.conn.execute(query,(var_name,))
        return cur.fetchone()[0]-1
    def get_regressors(self):
        regs_col=self.data_frame["variable"][self.data_frame["Interaction"]==0 ]
        return regs_col.get_values()

    def add_interactor(self,factor_rw_indexes):
        #get var_names
        if len(factor_rw_indexes)<2:
            #can't add interaction with just one factor
            return
        factor_indexes=[self.data_frame.index[i] for i in factor_rw_indexes]
        #check if already added:
        if frozenset(factor_indexes) in self.__interactors_dict.values():
            print "Trying to add duplicated interaction"
            return
        factor_names=self.data_frame["variable"].loc[factor_indexes]
        #create name
        interactor_name='*'.join(factor_names)
        print interactor_name
        #get degrees of freedom
        interactor_df=self.data_frame["DF"].loc[factor_indexes].prod()
        print interactor_df
        #add to dictionary
        interactor_idx=self.__next_index
        self.__next_index+=1
        self.__interactors_dict[interactor_idx]=frozenset(factor_indexes)
        #add to data frame
        self.beginInsertRows(QtCore.QModelIndex(),len(self.data_frame),len(self.data_frame))

        temp_data_frame=pd.DataFrame([(interactor_name,interactor_df,1)],columns=["variable","DF","Interaction"],
                                     index=(interactor_idx,))
        self.data_frame=self.data_frame.append(temp_data_frame)
        self.endInsertRows()
        self.update_display_view()

    def remove_invalid_interactions(self):
        index=frozenset(self.data_frame.index)
        to_remove=[]
        for k,v in self.__interactors_dict.iteritems():
            for i in v:
                if i not in index:
                    to_remove.append(k)
                    continue
        for k in to_remove:
            del self.__interactors_dict[k]
            self.data_frame.drop(k,inplace=True)
        print self.data_frame
        print self.__interactors_dict
    def get_data_frame(self):
        return self.data_frame
    def get_interactors_dict(self):
        return self.__interactors_dict



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

class AnovaResultsModel(QAbstractTableModel):
    def __init__(self,results_df=None):
        if results_df is None:
            self.__df=pd.DataFrame(None,columns=["Factor","Sum Sq","Df","F value","Pr(>F)"])
        else:
            self.__df=results_df
        super(AnovaResultsModel,self).__init__()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__df)
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.__df.shape[1]
    def data(self, QModelIndex, int_role=None):
        if not (int_role==QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line=QModelIndex.row()
        col=QModelIndex.column()
        return str(self.__df.iloc[line,col])
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            return self.__df.columns[p_int]
        return QtCore.QVariant()
    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse=True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse=False
        self.__df.sort(self.__df.columns[p_int],ascending=reverse,inplace=True)
        self.modelReset.emit()
    def flags(self, QModelIndex):
        line=QModelIndex.row()
        col=QModelIndex.column()
        result=QtCore.Qt.NoItemFlags
        if 0<=line<=self.rowCount() and 0<=line<=self.columnCount():
            result|=QtCore.Qt.ItemIsSelectable
            result|=QtCore.Qt.ItemIsEnabled
        return result

class sampleTree(QAbstractItemModel):
    def __init__(self,columns=None):
        super(sampleTree,self).__init__()
        if columns is None:
            columns=["lat","UBIC3","GENERO"]
        self.data_aspects=columns
        self.top_level=dict(enumerate(columns))
        self.top_level[-1]="All"
        self.__data_frame=braviz_tab_data.get_data_frame(columns)
        self.__headers={0: "Attribute",1:"N"}
        self.__str_to_ids_dict={}
        self.__ids_to_str_dict={}
        self.populate_ids()

    def populate_ids(self):
        for sufix in "nl":
            for top in self.top_level.itervalues():
                #Top Level
                sid=":".join((sufix,top))
                nid=len(self.__str_to_ids_dict)
                self.__str_to_ids_dict[sid]=nid
                self.__ids_to_str_dict[nid]=sid
            for subj in self.__data_frame.index:
                sid=":".join((sufix,"All",str(subj)))
                nid=len(self.__str_to_ids_dict)
                self.__str_to_ids_dict[sid]=nid
                self.__ids_to_str_dict[nid]=sid

    def parent(self, QModelIndex=None):
        if not QModelIndex.isValid():
            return QtCore.QModelIndex()
        nid=QModelIndex.internalId()
        sid=self.__ids_to_str_dict[nid]
        tokens=sid.split(":")
        if len(tokens)==2:
            return QtCore.QModelIndex()
        sid2=":".join(("l",tokens[1]))
        nid2=self.__str_to_ids_dict[sid2]
        #TODO: Only works with all
        return self.createIndex(0,0,nid2)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            return(len(self.data_aspects)+1)
        nid=QModelIndex_parent.internalId()
        sid=self.__ids_to_str_dict[nid]
        tokens=sid.split(":")
        if tokens[1]=="All":
            return len(self.__data_frame)
        return 0
    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2
    def data(self, QModelIndex, int_role=None):
        if int_role==QtCore.Qt.DisplayRole:
            parent=QModelIndex.parent()
            row=QModelIndex.row()
            col=QModelIndex.column()
            nid=QModelIndex.internalId()
            sid=self.__ids_to_str_dict[nid]
            #print sid

            if not parent.isValid():
                if col==0:
                    return self.top_level.get(row-1,QtCore.QVariant())
                elif col==1:
                    return len(self.__data_frame)
            else:
                nid=QModelIndex.internalId()
                sid=self.__ids_to_str_dict[nid]
                tokens=sid.split(":")
                if tokens[0]=="n":
                    return 1
                if tokens[1]=="All":
                    return tokens[2]

        return QtCore.QVariant()
    def index(self, p_int, p_int_1, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            #top level
            if p_int>=len(self.top_level) or p_int<0:
                return QtCore.QModelIndex()
            suffix="n" if p_int_1==1 else "l"
            top_str=self.top_level[p_int-1]
            index_str=":".join((suffix,top_str))
            nid=self.__str_to_ids_dict[index_str]
            out_index=self.createIndex(p_int,p_int_1,nid)
            assert out_index.isValid()
            return out_index
        else:
            sid=self.__ids_to_str_dict[QModelIndex_parent.internalId()]
            tokens=sid.split(":")
            if tokens[1]=="All":
                suffix="l"
                if p_int_1==1:
                    suffix="n"
                subj=self.__data_frame.index[p_int]
            sid2=":".join((suffix,tokens[1],str(subj)))
            nid=self.__str_to_ids_dict[sid2]
            out_index= self.createIndex(p_int,p_int_1,nid)
            assert out_index.isValid()
            return out_index


    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation==QtCore.Qt.Horizontal and int_role==QtCore.Qt.DisplayRole:
            self.__headers.get(p_int,QtCore.QVariant())
            return self.__headers.get(p_int,QtCore.QVariant())
        return QtCore.QVariant()
    def hasChildren(self, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            return True
        row=QModelIndex_parent.row()
        col=QModelIndex_parent.column()
        str_index=self.__ids_to_str_dict[QModelIndex_parent.internalId()]
        #print str_index
        if str_index=="l:All":
            return True


        return False

