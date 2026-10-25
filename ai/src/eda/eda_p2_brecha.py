import pandas as pd, numpy as np
import sys; p=(sys.argv[1] if len(sys.argv)>1 else 'data/processed').rstrip('/')+'/'
e=pd.read_parquet(p+'tabla_municipios_entrenamiento.parquet')
b=e.brecha_intermedia_presidencial*100
print('Brecha por foto (puntos)')
g=e.assign(b=b).groupby('eleccion_objetivo').b.describe(percentiles=[.1,.5,.9]).round(1)
g['vacias']=e.assign(b=b).groupby('eleccion_objetivo').b.apply(lambda s:s.isna().sum()); print(g.to_string())
print('\nBrecha negativa (mas abstencion en presidencial):',e.assign(b=b).groupby('eleccion_objetivo').b.apply(lambda s:(s<0).mean()*100).round(1).to_dict())
# variacion por estado y tipo de zona/tamaño (foto 2021 y 2024 como ejemplos con ambos tipos de historial)
for f in (2018,2021,2024):
    s=e[e.eleccion_objetivo==f].assign(b=b).dropna(subset=['b'])
    st=s.groupby('nombre_estado').b.median()
    print(f'\nFoto {f}: mediana por estado min {st.min():.1f} ({st.idxmin()}), max {st.max():.1f} ({st.idxmax()}); sd entre municipios {s.b.std():.1f}')
    s['zona']=pd.cut(s.pct_rural,[-.01,.05,.5,1.01],labels=['urbano (<5% rural)','mixto','rural (>50%)'])
    print(s.groupby('zona',observed=True).b.agg(['count','median']).round(1).to_string())
    s['tam']=pd.qcut(s.ln_ultima,3,labels=['chico','mediano','grande'])
    print(s.groupby('tam',observed=True).b.agg(['count','median']).round(1).to_string())
    # varianza explicada por estado (eta^2)
    eta=1-((s.b-s.groupby('nombre_estado').b.transform('mean'))**2).sum()/((s.b-s.b.mean())**2).sum(); print('  parte de la variacion que explica el estado: %.0f%%'%(eta*100))
# utilidad: ¿la brecha predice el error de repetir? solo intermedias (2015 y 2021) con brecha
print('\nUtilidad en fotos de intermedia')
for f in (2015,2021):
    s=e[e.eleccion_objetivo==f].assign(b=b).dropna(subset=['b','abstencion_objetivo','abst_ultima_intermedia'])
    err=(s.abstencion_objetivo-s.abst_ultima_intermedia)*100
    # tambien frente al nivel: brecha ya incluye el nivel de intermedias; usar abst_prom_presidenciales
    pres=s.abst_prom_presidenciales*100
    print(f,'n',len(s),'| corr(brecha, error con signo) %.2f'%np.corrcoef(s.b,err)[0,1],'| corr(brecha,|error|) %.2f'%np.corrcoef(s.b,err.abs())[0,1],
      '| corr(abst presidencial previa, error) %.2f'%np.corrcoef(pres,err)[0,1],'| corr(brecha, abst. objetivo) %.2f'%np.corrcoef(s.b,s.abstencion_objetivo)[0,1])
    # R2 parcial: añade brecha / presidencial a repetir
    X=np.c_[np.ones(len(s)),s.abst_ultima_intermedia*100]; y=s.abstencion_objetivo*100
    r2=lambda X:1-((y-X@np.linalg.lstsq(X,y,rcond=None)[0])**2).sum()/((y-y.mean())**2).sum()
    print('   R2 con solo ultima intermedia %.3f | + presidencial previa %.3f | + brecha %.3f'%(r2(X),r2(np.c_[X,pres]),r2(np.c_[X,s.b])))
