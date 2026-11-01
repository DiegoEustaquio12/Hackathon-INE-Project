# Escenarios con intervención (Fase 8)

**El efecto de cada intervención es un supuesto declarado, no un resultado estimado con estos datos.** Los escenarios parten de la predicción municipal publicada en la Fase 7, con el mismo modelo y los mismos cortes del semáforo; no se reentrena nada y no se simula una acción real del INE.

## Semáforo

Tres colores por orden de la abstención predicha. El corte rojo es **49.318%** y el amarillo **36.933%**. Los cortes se fijan una vez en el escenario sin intervención y se reutilizan en todas las intervenciones, para que los colores sean comparables. Los municipios sin personas con dato (12) quedan en gris y no reciben intervención.

| Color | Municipios |
|---|---|
| rojo | 821 |
| amarillo | 821 |
| verde | 823 |
| sin_clasificar | 12 |

El corte rojo queda **1.16 pp** por encima del nivel nacional publicado (48.162%), de modo que el tercio rojo reúne a los municipios claramente por encima del promedio nacional.

## Intervenciones

Cada intervención se aplica **solo en los municipios rojos** y se corre por separado: los grupos se traslapan, así que sus efectos no se suman. La reducción de la abstención es

```
reducción = efecto × parte de la lista del grupo × abstención del grupo
```

La parte del grupo se aplica de forma proporcional a las personas con dato: se supone que quienes no tienen dato se reparten como quienes sí lo tienen. Así la reducción queda acotada y no se dispara en municipios con mucho NS. Para jóvenes se combinan los tramos 18–24 y 25–34 con su abstención ponderada; para hombres se usa `1 − pct_mujeres`; para rural, `pct_rural`. Si un municipio no tiene secciones rurales, la reducción rural es cero.

## Resultados al efecto primario

| Intervención | Efecto (%) | Rojos | Con efecto | Salen de rojo | % de rojos | Reducción media (pp) | Mediana (pp) | Máxima (pp) | Ponderada (pp) |
|---|---|---|---|---|---|---|---|---|---|
| Jóvenes de 18 a 34 | 10.000 | 821 | 821 | 129 | 15.713 | 2.293 | 2.268 | 4.233 | 2.442 |
| Hombres | 10.000 | 821 | 821 | 173 | 21.072 | 2.765 | 2.747 | 4.024 | 2.818 |
| Zonas rurales | 10.000 | 821 | 617 | 105 | 12.789 | 1.402 | 1.127 | 6.639 | 0.723 |

La reducción media se calcula sobre los municipios rojos. «Salen de rojo» cuenta los que quedan por debajo del corte rojo al aplicar la intervención; el resto conserva su color. «Con efecto» cuenta los rojos donde el grupo objetivo existe: en rural excluye los municipios sin secciones rurales.

## Dónde rinde más

Municipios con mayor reducción absoluta al efecto primario:

| Intervención | Estado | Municipio | Reducción (pp) | Sin intervención (%) | Con intervención (%) |
|---|---|---|---|---|---|
| Jóvenes de 18 a 34 | OAXACA | Santiago Amoltepec | 4.230 | 76.256 | 72.023 |
| Jóvenes de 18 a 34 | OAXACA | Santa María Zaniza | 4.170 | 71.756 | 67.590 |
| Jóvenes de 18 a 34 | OAXACA | Santos Reyes Yucuná | 4.150 | 71.440 | 67.295 |
| Jóvenes de 18 a 34 | OAXACA | San Lucas Camotlán | 4.070 | 76.299 | 72.227 |
| Jóvenes de 18 a 34 | OAXACA | Coicoyán de las Flores | 3.970 | 75.229 | 71.256 |
| Hombres | OAXACA | San Lucas Camotlán | 4.020 | 76.299 | 72.275 |
| Hombres | OAXACA | Santos Reyes Pápalo | 3.870 | 74.776 | 70.911 |
| Hombres | OAXACA | San Jorge Nuchita | 3.830 | 75.679 | 71.853 |
| Hombres | OAXACA | San Juan Bautista Jayacatlán | 3.820 | 69.193 | 65.372 |
| Hombres | OAXACA | San Jacinto Tlacotepec | 3.800 | 69.541 | 65.738 |
| Zonas rurales | GUERRERO | Ñuu Savi | 6.640 | 51.100 | 44.461 |
| Zonas rurales | OAXACA | Santiago Amoltepec | 5.780 | 76.256 | 70.475 |
| Zonas rurales | CHIHUAHUA | Riva Palacio | 5.600 | 60.041 | 54.446 |
| Zonas rurales | OAXACA | San Juan Tamazola | 5.560 | 68.578 | 63.021 |
| Zonas rurales | OAXACA | Coicoyán de las Flores | 5.410 | 75.229 | 69.824 |

Entidades donde más municipios salen de rojo al efecto primario, por intervención:

| Intervención | Estado | salen_de_rojo |
|---|---|---|
| Hombres | OAXACA | 39 |
| Jóvenes de 18 a 34 | OAXACA | 33 |
| Hombres | VERACRUZ | 23 |
| Jóvenes de 18 a 34 | VERACRUZ | 19 |
| Hombres | JALISCO | 17 |
| Zonas rurales | OAXACA | 17 |
| Jóvenes de 18 a 34 | JALISCO | 14 |
| Zonas rurales | VERACRUZ | 13 |
| Zonas rurales | DURANGO | 11 |
| Hombres | ZACATECAS | 10 |

## Regla provisional de rural

De los 821 municipios rojos, 145 (17.7%) tienen más de la mitad de sus abstencionistas en secciones rurales. La intervención rural **se conserva**.

## Límites

- El efecto es un supuesto, no una estimación causal. El mapa de diferencia mide el tamaño del supuesto.
- Las tres intervenciones se traslapan y no deben sumarse.
- Los municipios con pocos casos conservan su marca y su reducción es más incierta.
- El escenario sin intervención tampoco es un contrafactual: los datos ya incluyen lo que el INE hizo hasta 2024.
- Los cortes del semáforo siguen pendientes de ratificación del equipo; aquí se implementa la propuesta de Fase 5.

## Reproducción

```
python ai/src/models/fase8.py
python -m unittest ai/tests/test_fase8.py
```

Las salidas están en `ai/artifacts/fase8/`. La tabla ancha alimenta los mapas; la larga guarda la sensibilidad de 5%, 10% y 15%.
