import pandas as pd, numpy as np
import sys; p=(sys.argv[1] if len(sys.argv)>1 else 'data/processed').rstrip('/')+'/'
e=pd.read_parquet(p+'tabla_municipios_entrenamiento.parquet')
def wcorr(x,y,w):
    mx,my=np.average(x,weights=w),np.average(y,weights=w)
    c=np.average((x-mx)*(y-my),weights=w)
    return c/np.sqrt(np.average((x-mx)**2,weights=w)*np.average((y-my)**2,weights=w))
def run(d,label):
    out=[]
    for f in (2015,2021):
        s=d[(d.eleccion_objetivo==f)].dropna(subset=['abstencion_objetivo','abst_ultima_intermedia'])
        x,y,w=s.abst_ultima_intermedia.values,s.abstencion_objetivo.values,s.conocidos_objetivo.values
        err=y-x
        sh=np.average(err,weights=w)  # sesgo ponderado (desplazamiento nacional)
        out.append(dict(foto=f,n=len(s),pearson=np.corrcoef(x,y)[0,1],spearman=s[['abst_ultima_intermedia','abstencion_objetivo']].corr('spearman').iloc[0,1],
            pearson_pond=wcorr(x,y,w),mae_pts=np.abs(err).mean()*100,mae_pond_pts=np.average(np.abs(err),weights=w)*100,
            desplaz_pond_pts=sh*100, mae_sin_desplaz_pts=np.abs(err-err.mean()).mean()*100,
            prom_x=x.mean()*100,prom_y=y.mean()*100,sd_x=x.std()*100,sd_y=y.std()*100,
            pendiente=np.polyfit(x,y,1)[0]))
    r=pd.DataFrame(out).round(3); print('\n==',label); print(r.T.to_string())
run(e,'todas las filas con dato')
run(e[~e.historial_rearmado & ~e.historial_incompleto],'sin rearmado/incompleto')
run(e[e.conocidos_ultima>=500],'conocidos_ultima>=500')
# nacional ponderado de abstencion_objetivo y de ultima intermedia
for f in (2015,2021):
    s=e[(e.eleccion_objetivo==f)].dropna(subset=['abstencion_objetivo','abst_ultima_intermedia'])
    print(f,'nacional pond: antes',round(np.average(s.abst_ultima_intermedia,weights=s.conocidos_ultima)*100,2),'despues',round(np.average(s.abstencion_objetivo,weights=s.conocidos_objetivo)*100,2))
# cuartiles de abstencion previa -> abstencion objetivo
for f in (2015,2021):
    s=e[(e.eleccion_objetivo==f)].dropna(subset=['abstencion_objetivo','abst_ultima_intermedia']).copy()
    s['q']=pd.qcut(s.abst_ultima_intermedia,4,labels=['Q1 baja','Q2','Q3','Q4 alta'])
    g=s.groupby('q',observed=True).agg(n=('q','size'),antes=('abst_ultima_intermedia','mean'),despues=('abstencion_objetivo','mean'))
    # rank persistence: share of Q4 that remain in top quartile
    s['q2']=pd.qcut(s.abstencion_objetivo,4,labels=False); s['q1']=pd.qcut(s.abst_ultima_intermedia,4,labels=False)
    print('\nFoto',f); print((g*[1,100,100]).round(1).to_string())
    print('Q4 previa que sigue en Q4 objetivo: %.1f%%'%((s[s.q1==3].q2==3).mean()*100), '| acierto exacto de cuartil: %.1f%%'%((s.q1==s.q2).mean()*100))
