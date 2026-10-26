"""Pregunta 3: nivel nacional y semáforo."""
import numpy as np
import pandas as pd
from eda_common import REPORT_DIR, markdown, plotting, run_question, save


def question3(base, train, out):
    e, m = train, base
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

    national = save(nat.rename("abstencion_pct").rename_axis("eleccion").reset_index(), "p3_abstencion_nacional", out)
    errors = save(pd.DataFrame(rows), "p3_error_nivel_nacional", out)
    colours = save(pd.DataFrame(sem), "p3_semaforo", out)
    return ["## Pregunta 3. ¿Cuánto se mueve el país entre intermedias? ¿Semáforo por nivel o por orden?",
            "**Respuesta:** el país se mueve entre 3 y 5 puntos entre intermedias, pero eso explica poco del error municipal. "
            "Con los dos esquemas estudiados, una parte importante de los municipios cambia de color.",
            "**Abstención nacional** (suma de todos los municipios):", markdown(national),
            "Las intermedias tienen solo dos cambios observados; no alcanzan para proyectar 2027.",
            "Error de repetir la última intermedia, comparado con repetir la diferencia contra el nivel nacional ya observado:",
            markdown(errors[["foto", "n", "MAE_nivel", "MAE_dif_con_pais_real"]]),
            "Qué pasa con un semáforo de tres colores:",
            markdown(colours[["foto", "cambia_color_nivel_fijo", "cambia_color_por_orden", "rojos_nivel_fijo",
                              "rojo_previo_sigue_rojo_orden"]]),
            "Por nivel, los rojos se encogen cuando el país mejora. Por orden (terciles), el rojo siempre es aproximadamente "
            "un tercio y se mantiene más, pero también cambia de color una parte importante de los municipios.",
            "**Decisión que apoya (propuesta; decide el equipo en la Fase 5):** cortar por orden, con terciles de la predicción 2027. "
            "Hay que decir en el reporte que el color es relativo al resto del país. El rango de la predicción importa tanto como el número.",
            "Se excluyen de la comparación de 2021 los 30 municipios sin dato de 2015, cuya última intermedia es 2009. "
            "Detalle: `p3_abstencion_nacional.csv`, `p3_error_nivel_nacional.csv` y `p3_semaforo.csv`."]


def main():
    run_question(3, question3, __file__)


if __name__ == "__main__":
    main()
