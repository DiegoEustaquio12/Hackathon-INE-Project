# Sección 7 de `reto_y_datos.md` y partes por sincronizar

Este archivo tiene dos partes:

- **Parte B:** la sección 7 de `reto_y_datos.md`, ya actualizada.
- **Parte C:** otras frases de `reto_y_datos.md` que hay que cambiar para que el documento quede sincronizado con la Fase 5.

**Estado:** todo es **propuesto**, pendiente de aprobación del equipo.

---

## Parte B. Sección 7 de `reto_y_datos.md`

## 7. Decisiones de la Fase 5 (propuestas)

Estas decisiones se toman con lo que mostró el análisis exploratorio, en la Fase 5 del [plan](PLAN.md). Si una cambia aquí, se cambia también allá.

1. **¿Qué es una "zona"?** El **municipio**, para el modelo, los escenarios, el semáforo, los mapas y el reporte. La sección se conserva como insumo de agregación y validación.
2. **¿Qué es "riesgo"?** El **nivel de abstención** del municipio (no la abstención por encima de lo esperado).
3. **Elección objetivo.** La intermedia de **2027**.
4. **Semáforo.** **3 colores**, cortados **por orden** (terciles de la predicción 2027 sin intervención). Los cortes se fijan una vez y son los mismos con intervención. El color es relativo al resto del país.
5. **Intervenciones hipotéticas.** **Tres**, por separado: jóvenes de 18 a 34, hombres y zonas rurales. Se aplican solo en los municipios rojos del escenario sin intervención. Efecto supuesto: 10% de los abstencionistas del grupo objetivo vota, con sensibilidad de 5% y 15%. Rural tiene una regla provisional: si en 2027 resultan muy pocos municipios rojos con mayoría de abstencionistas rurales, se cambia por 60 o más.
6. **Tratamiento de `NS`.** Se excluye del cálculo, como el INE. Se prueba contarlos como "no votó" y limitar a municipios con máximo 10% y 20% de NS. Los municipios con más de 50% de NS se marcan como de baja confianza. El 2012 se conserva marcado como incompleto, sin rellenar, y se prueba un historial sin 2012.
7. **Datos externos.** Se añaden los **ECEG 2010 y 2020 del INEGI**, con el censo más reciente anterior a cada elección. No se usan los Censos Económicos. La cartografía (contornos) probablemente sí se puede usar. *Falta confirmar con el INE ambos puntos.*
8. **Municipios sin historial, reconstruidos o sin dato.** Los registros sin respuesta se excluyen del entrenamiento y salen en gris en el mapa. Los reconstruidos se conservan y se evalúan por separado. Se reporta la cobertura. No se imputan.
9. **Tamaño mínimo de municipio.** Regla base de **500 personas con dato**, con sensibilidad a 100 y 1,000.

---

## Partes de `reto_y_datos.md` que hay que sincronizar


- **Sección 1:** en la tabla de la herramienta, la fila "Datos" habla de la participación histórica y del CCPC; hay que agregar los ECEG. La frase "Dónde concentrar acciones" sigue igual.
- **Sección 5, punto 1:** dice "No podemos usar datos externos". Hay que matizar: se usan los ECEG, pendiente de confirmar con el INE.
- **Sección 5, punto 2:** habla de seguir secciones entre elecciones. Con municipio como zona, sigue siendo necesario para reconstruir el historial, pero conviene decir que la unidad final es el municipio.
- **Sección "Fase final opcional":** la tabla de escenarios dice "Identificador de la zona (estado + sección)... distrito federal". Cambiar a estado + municipio.
- **Sección 3 (mapas):** los mapas 3 y 4 siguen como propuesta. Con la regla de "solo en rojos", el mapa 3 vale cero fuera de los rojos; conviene anotarlo en la leyenda.
- **Sección 6, "Niveles de análisis":** sigue siendo cierto que todo se suma desde la sección. Agregar que el nivel final es el municipio.
