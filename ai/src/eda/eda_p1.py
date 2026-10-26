"""Pregunta 1: persistencia de la abstención entre intermedias."""
import numpy as np
import pandas as pd
from eda_common import REPORT_DIR, markdown, plotting, run_question, save


def figure(e):
    plt = plotting()
    INK,MUTED,GRID,BLUE,ORANGE='#1f2933','#5f6b7a','#e3e7ec','#2f6fb5','#c8541a'
    fig,axs=plt.subplots(1,2,figsize=(11,5.2),sharex=True,sharey=True,dpi=150)
    for ax,f in zip(axs,(2015,2021)):
        s=e[e.eleccion_objetivo==f].dropna(subset=['abstencion_objetivo','abst_ultima_intermedia'])
        x,y=s.abst_ultima_intermedia*100,s.abstencion_objetivo*100
        sz=np.clip(np.sqrt(s.conocidos_objetivo)/6,2,60)
        ax.scatter(x,y,s=sz,color=BLUE,alpha=.35,linewidths=0)
        ax.plot([0,100],[0,100],color=MUTED,lw=1,ls='--')
        b,a=np.polyfit(x,y,1); xs=np.array([0,100]); ax.plot(xs,a+b*xs,color=ORANGE,lw=2)
        r=np.corrcoef(x,y)[0,1]
        ax.set_title(f'Foto {f}  (r = {r:.2f}, pendiente = {b:.2f})',color=INK,fontsize=11,loc='left')
        ax.text(97,3,'línea punteada: "repite igual"\nlínea naranja: tendencia real',ha='right',va='bottom',fontsize=8,color=MUTED)
        ax.set_xlabel('Abstención en la última intermedia anterior (%)',color=MUTED,fontsize=9)
        ax.grid(color=GRID,lw=.8); ax.set_axisbelow(True)
        for sp in ('top','right'): ax.spines[sp].set_visible(False)
        for sp in ('left','bottom'): ax.spines[sp].set_color(GRID)
        ax.tick_params(colors=MUTED,labelsize=8); ax.set_xlim(0,100); ax.set_ylim(0,100)
    axs[0].set_ylabel('Abstención que hubo (%)',color=MUTED,fontsize=9)
    fig.suptitle('¿El municipio que se abstuvo mucho lo repite? Cada punto es un municipio (tamaño = personas con dato)',x=.06,ha='left',fontsize=12,color=INK)
    fig.tight_layout(rect=(0,0,1,.94)); fig.savefig(REPORT_DIR / "eda_p1_dispersion.png"); plt.close(fig)


def question1(base, train, out):
    e = train
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
        r=pd.DataFrame(out); print('\n==',label); print(r.round(3).T.to_string()); return r
    all_rows = run(e,'todas las filas con dato')
    clean_rows = run(e[~e.historial_rearmado & ~e.historial_incompleto],'sin rearmado/incompleto')
    large_rows = run(e[e.conocidos_ultima>=500],'conocidos_ultima>=500')
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

    summary = all_rows[["foto", "n", "pearson", "mae_pts", "mae_pond_pts"]].copy()
    save(all_rows, "p1_persistencia", out)
    save(clean_rows, "p1_sin_reconstruccion", out)
    save(large_rows, "p1_minimo_500", out)
    quartiles = []
    for year in (2015, 2021):
        s = e[e.eleccion_objetivo == year].dropna(subset=["abstencion_objetivo", "abst_ultima_intermedia"]).copy()
        s["cuartil_previo"] = pd.qcut(s.abst_ultima_intermedia, 4, labels=False)
        s["cuartil_objetivo"] = pd.qcut(s.abstencion_objetivo, 4, labels=False)
        for group, d in s.groupby("cuartil_previo"):
            quartiles.append(dict(foto=year, cuartil=int(group)+1, municipios=len(d),
                                  antes_pct=d.abst_ultima_intermedia.mean()*100,
                                  despues_pct=d.abstencion_objetivo.mean()*100,
                                  sigue_en_cuartil_pct=100*(d.cuartil_objetivo == group).mean()))
    quartiles = save(pd.DataFrame(quartiles), "p1_cuartiles", out)
    figure(e)
    return ["## Pregunta 1. ¿Quien se abstuvo mucho en una intermedia lo repite en la siguiente?",
            "**Respuesta:** en parte. Es la base de la predicción, pero se equivoca bastante.",
            markdown(summary.rename(columns={"foto": "Foto", "n": "Municipios comparados", "pearson": "Correlación",
                                             "mae_pts": "Error de repetir (puntos)", "mae_pond_pts": "Error ponderado (puntos)"})),
            "Los municipios con mucha abstención tienden a repetirla, pero la relación es moderada y se debilitó "
            "entre las dos comparaciones. Los CSV incluyen la comparación sin historial rearmado o incompleto "
            "y con al menos 500 personas con dato en la elección previa.",
            "Cuartiles de abstención previa: Q1 es el cuarto de municipios con menor abstención y Q4 el de mayor abstención.",
            markdown(quartiles),
            "**Cuidado:** solo hay dos fotos de intermedias, así que no sabemos si el debilitamiento es tendencia o casualidad.",
            "**Decisión que apoya:** la Fase 7 tiene que ganarle al error de repetir la última intermedia en la foto de 2021.",
            "![Dispersión](eda_p1_dispersion.png)",
            "Detalle: `p1_persistencia.csv`, `p1_sin_reconstruccion.csv`, `p1_minimo_500.csv` y `p1_cuartiles.csv`."]


def main():
    run_question(1, question1, __file__)


if __name__ == "__main__":
    main()
