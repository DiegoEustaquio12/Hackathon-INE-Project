// textos de presentacion: nombres, preguntas de cada vista y razones en lenguaje sencillo

// los datos traen los estados en mayusculas y sin acentos
export const NOMBRE_ESTADO = {
  'AGUASCALIENTES': 'Aguascalientes', 'BAJA CALIFORNIA': 'Baja California', 'BAJA CALIFORNIA SUR': 'Baja California Sur',
  'CAMPECHE': 'Campeche', 'CHIAPAS': 'Chiapas', 'CHIHUAHUA': 'Chihuahua', 'CIUDAD DE MEXICO': 'Ciudad de México',
  'COAHUILA': 'Coahuila', 'COLIMA': 'Colima', 'DURANGO': 'Durango', 'GUANAJUATO': 'Guanajuato', 'GUERRERO': 'Guerrero',
  'HIDALGO': 'Hidalgo', 'JALISCO': 'Jalisco', 'MEXICO': 'Estado de México', 'MICHOACAN': 'Michoacán',
  'MORELOS': 'Morelos', 'NAYARIT': 'Nayarit', 'NUEVO LEON': 'Nuevo León', 'OAXACA': 'Oaxaca', 'PUEBLA': 'Puebla',
  'QUERETARO': 'Querétaro', 'QUINTANA ROO': 'Quintana Roo', 'SAN LUIS POTOSI': 'San Luis Potosí', 'SINALOA': 'Sinaloa',
  'SONORA': 'Sonora', 'TABASCO': 'Tabasco', 'TAMAULIPAS': 'Tamaulipas', 'TLAXCALA': 'Tlaxcala', 'VERACRUZ': 'Veracruz',
  'YUCATAN': 'Yucatán', 'ZACATECAS': 'Zacatecas',
};
export const nombreEstado = e => NOMBRE_ESTADO[e] || e;

// cada mapa: nombre de su pestaña y la linea "Que muestra" que se lee debajo
export const VISTAS = {
  sin: { num: 1, corto: 'Sin intervención', que: 'Qué porcentaje de la lista nominal no votaría en 2027 si nada cambia. Rojo: el tercio de municipios con más abstención.' },
  con: { num: 2, corto: 'Con intervención', que: 'Lo mismo, si se aplicara la intervención en los municipios en rojo.' },
  dif: { num: 3, corto: 'Cuánto baja', que: 'Cuántos puntos bajaría la abstención con la intervención. 1 punto = 1 de cada 100 personas de la lista nominal.' },
  brecha: { num: 4, corto: 'Intermedia vs. presidencial', que: 'Cuántos puntos más se abstiene cada municipio en elecciones intermedias que en presidenciales.' },
};
export const QUE_COMPARAR = {
  cortina: 'Izquierda: sin intervención. Derecha: con intervención. Arrastra la barra blanca.',
  lado: 'Izquierda: sin intervención. Derecha: con intervención. Los dos mapas se mueven juntos.',
};

export const GRUPOS = {
  jovenes: { nombre: 'Jóvenes (18–34)', frase: 'jóvenes de 18 a 34 años' },
  hombres: { nombre: 'Hombres', frase: 'hombres' },
  rural: { nombre: 'Zonas rurales', frase: 'personas de zonas rurales' },
};
export const GRUPO_IDX = { jovenes: 0, hombres: 1, rural: 2 };

// "1 de cada 10" para el efecto supuesto
export const FRACCION = { 5: '1 de cada 20', 10: '1 de cada 10', 15: '15 de cada 100' };

// banderas de calidad (campo av de escenarios.json)
export const BANDERAS = {
  'pocos casos': { nombre: 'Pocos casos', texto: 'Hay pocas personas con dato de si votaron o no.' },
  'NS alto': { nombre: 'Muchos sin dato', texto: 'De muchas personas de la lista no se sabe si votaron.' },
  'sin censo': { nombre: 'Sin censo', texto: 'No hay datos del censo del INEGI para este municipio.' },
};

// las 12 razones que da el modelo, reescritas; si llega una nueva se muestra tal cual
const RAZONES = {
  'Abstención de la última presidencial antes de la elección que se predice': 'Cuánto se abstuvo en la última elección presidencial',
  'La última presidencial menos la del país en esa elección': 'Su abstención frente al resto del país en la última presidencial',
  'Si la elección objetivo es intermedia': 'Que 2027 sea elección intermedia (no se elige presidente)',
  'Promedio de la abstención de todas las presidenciales anteriores': 'Su abstención promedio en las presidenciales anteriores',
  'La última intermedia menos la del país en esa elección (positivo = se abstiene más que el país)': 'Su abstención frente al resto del país en la última intermedia',
  'Parte de la lista de 35 a 44 años': 'Qué parte de la lista nominal tiene de 35 a 44 años',
  'Abstención de las personas de 18 a 24 años': 'Cuánto se abstienen las personas de 18 a 24 años',
  'Personas con dato (SV + NV) en la última elección': 'Cuántas personas tienen dato de si votaron en la última elección',
  'Cuánto cambió entre las dos últimas intermedias (positivo = subió). Vacío si solo hay una': 'Cómo cambió su abstención entre las dos últimas intermedias',
  'Parte de la lista que son mujeres': 'Qué parte de la lista nominal son mujeres',
  'Abstención de las personas de 45 a 59 años': 'Cuánto se abstienen las personas de 45 a 59 años',
  'Parte de la lista sin saber si votó, en la última elección': 'Qué parte de la lista no tiene dato de si votó',
};

// "texto: +3.43 pp de abstención" -> { texto, valor }
export function leerRazon(r) {
  const m = /^(.*):\s*([+\-−]?\d+(?:\.\d+)?)\s*pp/.exec(r);
  if (!m) return { texto: r, valor: null };
  const valor = parseFloat(m[2].replace('−', '-'));
  return { texto: RAZONES[m[1].trim()] || m[1].trim(), valor };
}
