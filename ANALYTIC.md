analytic/indicadores_financieros/indicadores-de-solvencia

CALCULOS:

Gasto Operativo / Activo Promedio

```
!GASTO OPERA ESTIMADO =
VAR GAST_OPE=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[45]/'1-CONSOLIDADO-'[MES]*12)
RETURN GAST_OPE

!ACTIVO PROMEDIO =
VAR MES=VALUES(CALENDARIO[MES])
VAR LAST=AVERAGEX(DATESINPERIOD(CALENDARIO[Date],MAX(CALENDARIO[Date]),-MES,MONTH),'1-CONSOLIDADO-'[!ACTIVOS])
RETURN LAST

!GASTO OPERATIVO ESTIMADO/ACTIVO PROMEDIO =
VAR GAST_ACT_PROM=[!GASTO OPERA ESTIMADO]/[!ACTIVO PROMEDIO]
RETURN GAST_ACT_PROM
```

Gasto Personal / Activo Promedio

```
!ACTIVO PROMEDIO =
VAR MES=VALUES(CALENDARIO[MES])
VAR LAST=AVERAGEX(DATESINPERIOD(CALENDARIO[Date],MAX(CALENDARIO[Date]),-MES,MONTH),'1-CONSOLIDADO-'[!ACTIVOS])
RETURN LAST

!GASTO PERSONAL ESTIMADO =
VAR GAST_PERSO=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[4501]/'1-CONSOLIDADO-'[MES]*12)
RETURN GAST_PERSO

!GASTO PERSONAL ESTIMADO/ACTIVO PROMEDIO =
VAR GAST_ACT_PROM=[!GASTO PERSONAL ESTIMADO]/[!ACTIVO PROMEDIO]
RETURN GAST_ACT_PROM}

```

Margen de intermediacion estimada / Patrimonio Promedio

```

MARGEN DE INTER ESTIMA/PATRIMO PROME = [!Margen de Intermediacion Estimado]/[!PATRIMONIO PROMEDIO] !Margen de Intermediacion Estimado =
var intereses_ganados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[51]/'1-CONSOLIDADO-'[MES]*12)
var intereses_causados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[41]/'1-CONSOLIDADO-'[MES]*12)
var margen_neto_intereses=intereses_ganados-intereses_causados
var comisiones_ganados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[52]/'1-CONSOLIDADO-'[MES]*12)
var ingr_serv=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[54]/'1-CONSOLIDADO-'[MES]*12)
var comis_causa=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[42]/'1-CONSOLIDADO-'[MES]*12)
var util_financiera=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[53]/'1-CONSOLIDADO-'[MES]*12)
var perd_finan=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[43]/'1-CONSOLIDADO-'[MES]*12)
var marge_brut_financie=(margen_neto_intereses+comisiones_ganados+ingr_serv-comis_causa+util_financiera-perd_finan)
var provisiones=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[44]/'1-CONSOLIDADO-'[MES]*12)
var marge_finan_neto=marge_brut_financie-provisiones
var gasto_oper=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[45]/'1-CONSOLIDADO-'[MES]*12)
var marg_inte_estimad=marge_finan_neto-gasto_oper
return marg_inte_estimad

!PATRIMONIO PROMEDIO =
VAR MES=VALUES(CALENDARIO[MES])
VAR LAST=AVERAGEX(DATESINPERIOD(CALENDARIO[Date],MAX(CALENDARIO[Date]),-MES,MONTH),'1-CONSOLIDADO-'[!PATRIMONIO])
RETURN LAST


MARGEN DE INTER ESTIMA/PATRIMO PROME = [!Margen de Intermediacion Estimado]/[!PATRIMONIO PROMEDIO]

```


Margen de Intermedacion estimado / Activo Promedio

```
!ACTIVO PROMEDIO =
VAR MES=VALUES(CALENDARIO[MES])
VAR LAST=AVERAGEX(DATESINPERIOD(CALENDARIO[Date],MAX(CALENDARIO[Date]),-MES,MONTH),'1-CONSOLIDADO-'[!ACTIVOS])
RETURN LAST

PROMEDIO] !Margen de Intermediacion Estimado =
var intereses_ganados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[51]/'1-CONSOLIDADO-'[MES]*12)
var intereses_causados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[41]/'1-CONSOLIDADO-'[MES]*12)
var margen_neto_intereses=intereses_ganados-intereses_causados
var comisiones_ganados=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[52]/'1-CONSOLIDADO-'[MES]*12)
var ingr_serv=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[54]/'1-CONSOLIDADO-'[MES]*12)
var comis_causa=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[42]/'1-CONSOLIDADO-'[MES]*12)
var util_financiera=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[53]/'1-CONSOLIDADO-'[MES]*12)
var perd_finan=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[43]/'1-CONSOLIDADO-'[MES]*12)
var marge_brut_financie=(margen_neto_intereses+comisiones_ganados+ingr_serv-comis_causa+util_financiera-perd_finan)
var provisiones=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[44]/'1-CONSOLIDADO-'[MES]*12)
var marge_finan_neto=marge_brut_financie-provisiones
var gasto_oper=SUMX('1-CONSOLIDADO-','1-CONSOLIDADO-'[45]/'1-CONSOLIDADO-'[MES]*12)
var marg_inte_estimad=marge_finan_neto-gasto_oper
return marg_inte_estimad

MARGEN DE INTER ESTIMA/ACT PROME = [!Margen de Intermediacion Estimado]/[!ACTIVO 

```