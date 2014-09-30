b_kmeans <- function(df,k){
  table2<-df[complete.cases(df),]
  row.names(table2)<-table2$subject
  vars = names(table2)
  table3=table2[,vars[2:length(vars)]]
  table3.standad = scale(table3)
  km = kmeans(table3.standad,k,iter.max = 100000,nstart = 100)
  table3$kmeans[names(km$cluster)]=km$cluster
  return(table3)
}

b_hclust<-function(df,k){
  table2<-df[complete.cases(df),]
  row.names(table2)<-table2$subject
  vars = names(table2)
  table3=table2[,vars[2:length(vars)]]
  table3.standad = scale(table3)  
  hc = hclust(dist(table3.standad))
  plot(hc)
  a=rect.hclust(hc,k=k,border="red")
  for (i in 1:k){
    table3[a[[i]],"clust"]=i
  }
  return(table3)
}