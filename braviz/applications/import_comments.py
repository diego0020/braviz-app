from braviz.readAndFilter import user_data
import pandas as pd
import sys

__author__ = 'da.angulo39'

def import_comments(excel_path,columns):
    df=pd.read_excel(excel_path,index_col=0)
    comments = {}
    for c in columns:
        col = df[c].dropna()
        for i in col.index:
            com1 = comments.setdefault(i,"")
            com2 = "\n".join((c,col[i]))
            if len(com1)>0:
                com3 = "\n\n".join((com1,com2))
            else:
                com3 = com2
            comments[i]=com3

    for k,v in comments.iteritems():
        print "%d : %s"%(k,v)
        user_data.update_comment(int(k),v)

if __name__ == "__main__":
    args = sys.argv()
    if len(args)<2:
        print """Imports comments from an excel file into the comments field of the database

        Usage:
        %s <path to excel file> [comment columns]

        If comment columns is empty, the defaults are used: "PEDIATRIA_Observaciones3","PEDIATRIA_AnosRepetidosRazon","NEURO_DiagnosticWMlesions"
        Otherwise, the comments are extracted from the columns with those names.
        """%args[0]
    path = args[1]
    if len(args)==2:
        cols = ["PEDIATRIA_Observaciones3",
                "PEDIATRIA_AnosRepetidosRazon",
                "NEURO_DiagnosticWMlesions"]
    else:
        cols = args[2:]
    import_comments(path,columns=cols)