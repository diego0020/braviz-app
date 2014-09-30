image(is.na(matrix)+0)
drops<-c("Raw_Pcm","SS_Pcm","Raw_CA","SS_CA")
matrix2<-matrix[,!(names(matrix) %in% drops)]
image(is.na(matrix2)+0)
sum(sapply(matrix2[44,],is.na))
matrix3<-matrix2[-44,]
image(is.na(matrix3)+0)

#find columns with many nas
lapply(matrix3,function(x) sum(is.na(x)))
!(sapply(matrix3,function(x) sum(is.na(x))))>0
matrix4<-matrix3[,!(sapply(matrix3,function(x) sum(is.na(x))))>0]
matrix4$UBIC3<-relevel(factor(matrix4$UBIC3),ref="3")
image(is.na(matrix4)+0)


model<-multinom(UBIC3 ~ . ,data=matrix4,na.action=na.omit)
library(nnetresultados_step<-stepAIC(model)
        
)
#Trees and forests

#Quitar variables obvias:
drops<-c("DURCANGURO","edadevaluacion","cohorte","BALLARD","PESNACER")
matrix5<-matrix4[,!(names(matrix4) %in% drops)]

library(tree)

t<-tree(UBIC3 ~ . ,data=matrix5)
plot(t)
text(t)
t

library(randomForest)
fit <- randomForest(UBIC3 ~ . ,data=matrix4,replace=T,importance=T)
fit <- randomForest(RCT1599 ~ . ,data=matrix4,replace=T,importance=T)

imp<-fit$importance
imp2<-imp[order(-imp[,5]),]write.csv(imp2,file="var_importance.csv")


fit <- randomForest(UBIC3 ~ . ,data=matrix,replace=T,importance=T,na.action=na.roughfix,ntree=50000)
fit$importance[order(fit$importance[,5]),]

#only use groups kmc and incubator
preterms<-matrix4[!matrix4$UBIC3==3,]
table(preterms$UBIC3)
preterms$UBIC3<-factor(preterms$UBIC3)
model=glm(UBIC3~., data=preterms,family="binomial")
step(model,direction="both")
model=glm(UBIC3~.-DURCANGURO, data=preterms,family="binomial")
library(Rcmdr)

stepwise(model,direction="forward")
#Tree
fit <- randomForest(UBIC3 ~ .-DURCANGURO-cohorte ,data=preterms,replace=T,importance=T,ntree=50000)
fit$importance[order(fit$importance[,4]),]

t<-tree(UBIC3~.-DURCANGURO-cohorte-DXFd-DXFnd,data=preterms,mindev=0.00005)
plot(t)
text(t)

#inspired in http://alandgraf.blogspot.com/search/label/Random%20forest
library(party)
cf1=cforest(UBIC3~.,data=matrix4)
vimpo<-varimp(cf1,conditional=T)
vimpo2<-vimpo[order(vimpo)]
write.csv(vimpo2,file="vimpo2.csv")

vimpo<-varimp(cf1,conditional=F)
vimpo2<-vimpo[order(vimpo)]
write.csv(vimpo2,file="vimpo_not_cond.csv")