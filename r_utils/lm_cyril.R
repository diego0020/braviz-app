#anova cyril

library("arm")

sum_matrix = matrix[c("GENERO","IHIlatd","FSIQ")]
sum_matrix$GENERO <- factor(sum_matrix$GENERO)
sum_matrix$UBIC <- relevel(factor(matrix$UBIC3),ref=1)


cyril.lm<-lm(IHIlatd ~ GENERO+UBIC+UBIC*FSIQ + GENERO*FSIQ ,data=sum_matrix)
display(cyril.lm)

cyril.lm2 <- standardize(cyril.lm,standardize.y=T)
display(cyril.lm2)
#coefplot(cyril.lm)
coefplot(cyril.lm2)

summary(cyril.lm2)
ci <- confint(cyril.lm2)

coef_plot.lm(cyril.lm2)