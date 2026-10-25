import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
import sys; p=(sys.argv[1] if len(sys.argv)>1 else 'data/processed').rstrip('/')+'/'
e=pd.read_parquet(p+'tabla_municipios_entrenamiento.parquet')
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
fig.tight_layout(rect=(0,0,1,.94)); fig.savefig('eda_p1_dispersion.png')
