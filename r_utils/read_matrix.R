setwd("C:\\Users\\Diego\\Documents\\R_workspace")
matrix<-read.table("test_small.csv",header=T,sep=";",row.names=1,na.strings="#NULL!",check.names=T,comment.char="",dec=",")
matrix$UBIC3<-factor(matrix$UBIC3)
matrix$GENERO<-factor(matrix$GENERO)

