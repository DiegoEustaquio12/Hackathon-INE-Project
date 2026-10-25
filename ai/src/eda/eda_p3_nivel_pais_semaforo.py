import pandas as pd, numpy as np
import sys; p=(sys.argv[1] if len(sys.argv)>1 else 'data/processed').rstrip('/')+'/'
e=pd.read_parquet(p+'tabla_municipios_entrenamiento.parquet')
m=pd.read_parquet(p+'municipio_eleccion.parquet')
nat=m.groupby('AELEC').apply(lambda d:d.NV.sum()/(d.SV.sum()+d.NV.sum())*100,include_groups=False)
print('1) Abstencion nacional (NV/(SV+NV), todos los municipios):'); print(nat.round(2).to_string())
tipo=m.groupby('AELEC').tipo_eleccion.first()
inter=nat[tipo=='intermedia']; print('\nCambio entre intermedias:',inter.diff().round(2).dropna().to_dict())
pres=nat[tipo=='presidencial']; print('Cambio entre presidenciales:',pres.diff().round(2).dropna().to_dict())
prev={2015:2009,2021:2015}
print('\n2) Error de repetir (puntos) y semaforo')
rows=[];sem=[]
for f,pv in prev.items():
    s=e[e.eleccion_objetivo==f].dropna(subset=['abstencion_objetivo','abst_ultima_intermedia']).copy()
    if f==2021: s=s[s.n_intermedias_previas==2]  # 30 municipios sin 2015: su 'ultima intermedia' es 2009
    x,y,w=s.abst_ultima_intermedia*100,s.abstencion_objetivo*100,s.conocidos_objetivo
    gx,gy=s.abst_ultima_intermedia_vs_pais*100,y-nat[f]
    # chequeo: la columna del diccionario
    chk=(s.abst_ultima_intermedia_vs_pais*100-gx).abs().max()
    rows.append(dict(foto=f,n=len(s),chk_col_vs_pais=round(chk,3),
      MAE_nivel=np.abs(y-x).mean(),MAE_dif_con_pais_real=np.abs(gy-gx).mean(),
      MAEpond_nivel=np.average(np.abs(y-x),weights=w),MAEpond_dif=np.average(np.abs(gy-gx),weights=w),
      sd_dif_prev=gx.std(),sd_dif_obj=gy.std(),corr_dif=np.corrcoef(gx,gy)[0,1]))
    # semaforo 3 colores: cortes por terciles de la eleccion previa
    c=np.quantile(x,[1/3,2/3])
    col_prev=np.digitize(x,c)                 # color previo (por orden = por nivel en la previa)
    col_nivel=np.digitize(y,c)                # cortes fijos por nivel (los de la previa)
    c2=np.quantile(y,[1/3,2/3]); col_orden=np.digitize(y,c2)  # terciles propios de la objetivo
    sem.append(dict(foto=f,cortes_prev=[round(v,1) for v in c],cortes_obj_terciles=[round(v,1) for v in c2],
      cambia_color_nivel_fijo=(col_prev!=col_nivel).mean()*100,cambia_color_por_orden=(col_prev!=col_orden).mean()*100,
      rojos_nivel_fijo=(col_nivel==2).mean()*100,rojos_prev=(col_prev==2).mean()*100,
      rojo_previo_sigue_rojo_nivel=(col_nivel[col_prev==2]==2).mean()*100,rojo_previo_sigue_rojo_orden=(col_orden[col_prev==2]==2).mean()*100,
      verde_sube_a_rojo_nivel=(col_nivel[col_prev==0]==2).mean()*100,verde_sube_a_rojo_orden=(col_orden[col_prev==0]==2).mean()*100))
print(pd.DataFrame(rows).round(2).T.to_string()); print()
print(pd.DataFrame(sem).T.to_string())
