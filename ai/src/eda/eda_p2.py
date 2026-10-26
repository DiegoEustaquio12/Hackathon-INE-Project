"""Pregunta 2: brecha entre intermedias y presidenciales."""
import numpy as np
import pandas as pd
from eda_common import REPORT_DIR, markdown, plotting, run_question, save


def question2(base, train, out):
    e = train
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

    distribution = e.assign(b=b).groupby("eleccion_objetivo").b.agg(
        municipios="count", mediana_pp="median", p10_pp=lambda s:s.quantile(.1), p90_pp=lambda s:s.quantile(.9)).reset_index()
    save(distribution, "p2_brecha", out)
    states = e.assign(b=b).groupby(["eleccion_objetivo", "nombre_estado"]).b.agg(
        municipios="count", mediana_pp="median").reset_index()
    save(states, "p2_brecha_estatal", out)
    fits = []
    for year in (2015, 2021):
        s = e[e.eleccion_objetivo == year].dropna(subset=["abstencion_objetivo", "abst_ultima_intermedia", "abst_prom_presidenciales"])
        y = s.abstencion_objetivo.to_numpy(dtype=float)*100
        x = np.c_[np.ones(len(s)), s.abst_ultima_intermedia.to_numpy(dtype=float)*100]
        xp = np.c_[x, s.abst_prom_presidenciales.to_numpy(dtype=float)*100]
        r2 = lambda a: 1-((y-a@np.linalg.lstsq(a,y,rcond=None)[0])**2).sum()/((y-y.mean())**2).sum()
        fits.append(dict(foto=year, municipios=len(s), r2_intermedia=r2(x), r2_con_presidencial=r2(xp)))
    fits = save(pd.DataFrame(fits), "p2_ajuste_exploratorio", out)
    return ["## Pregunta 2. ¿Cuánto más se abstienen en intermedias que en presidenciales? ¿Pasa igual en todos lados?",
            "**Respuesta:** mucho más, pero depende del estado. Casi nunca ocurre al revés.",
            "Brecha entre municipios, en puntos porcentuales:",
            markdown(distribution.rename(columns={"p90_pp": "Percentil 90 de la brecha (puntos)"})),
            "El archivo `p2_brecha_estatal.csv` muestra las diferencias por estado y elección. "
            "La salida de terminal conserva también las comparaciones por zona y tamaño.",
            "La historia presidencial ayuda en el ajuste exploratorio. Es un ajuste rápido sobre los mismos datos, no la prueba del modelo:",
            markdown(fits),
            "La brecha comparte cálculo con la última intermedia, así que conviene incluir también por separado "
            "las columnas presidenciales (`abst_ultima_presidencial`, `abst_prom_presidenciales`).",
            "**Cuidado:** en la foto 2015 la brecha usa una sola elección de cada tipo (2009 y 2012), y 2012 tiene huecos, así que es más ruidosa.",
            "**Decisión que apoya:** considerar `tipo_objetivo`, conservar el historial presidencial y preparar el mapa de brecha.",
            "Detalle: `p2_brecha.csv`, `p2_brecha_estatal.csv` y `p2_ajuste_exploratorio.csv`."]


def main():
    run_question(2, question2, __file__)


if __name__ == "__main__":
    main()
