#anova cyril
cyril.lm<-lm(IHIlatd ~ GENERO+UBIC3+UBIC3:GENERO,data=matrix)
summary(cyril.lm)
cyril.anova<-anova(cyril.lm)
print(cyril.anova)

cyril.aov<-aov(IHIlatd ~ GENERO+UBIC3+UBIC3:GENERO,data=matrix)
cyril.THSD<-TukeyHSD(cyril.aov)
print(cyril.THSD)
