// estado unico de la pagina, datos cargados, categorias de color y sincronizacion con la URL
import { GRUPO_IDX } from './textos.js';

export const datos = { DATA: null, GEO: null, ESTADOS: null };

export const estado = {
  vista: 'sin',        // sin | con | dif | brecha
  grupo: 'jovenes',    // grupo objetivo de la intervencion
  efecto: '10',        // efecto supuesto (%)
  comparar: '',        // '' | 'lado' | 'cortina'
  mun: null,           // CVEGEO del municipio seleccionado
  ocultas: new Set(),  // categorias apagadas en la leyenda
  fragiles: false,     // resaltar datos fragiles
  panel: 'mapa',       // mapa | lista
  edo: '',             // filtro de estado en la lista (2 digitos)
  soloFragiles: false, // filtro de la lista
  orden: '',           // orden de la lista: "columna:asc|desc"
  presentar: false,
};

// ---------- avisos de cambio ----------
const oyentes = [];
export const alCambiar = f => oyentes.push(f);
export function cambiar(parcial) {
  const escalaAntes = escala();
  Object.assign(estado, parcial);
  if (escala() !== escalaAntes && !('ocultas' in parcial)) estado.ocultas = new Set();
  if ('grupo' in parcial || 'efecto' in parcial) recalcular();
  oyentes.forEach(f => f(parcial));
  escribirURL();
}

// ---------- escenario del municipio ----------
// [abstencion con intervencion, color con intervencion, reduccion en pp]
export const escenario = d => d.esc[estado.grupo][estado.efecto];
export const cambioColor = d => d.cs !== 0 && escenario(d)[1] !== d.cs;
export const grupoPct = d => d.gr[GRUPO_IDX[estado.grupo]];

// vista que pinta cada mapa: al comparar, el mapa A es "sin" y el B es "con"
export const vistaMapa = cual => (estado.comparar ? (cual === 'B' ? 'con' : 'sin') : estado.vista);
// vista que manda en leyenda y lista
export const vistaActiva = () => (estado.comparar ? 'comparar' : estado.vista);

// ---------- categorias y colores ----------
export const COLORES = {
  alto: '#a51f2a', medio: '#f2c230', bajo: '#6dbaa0', nd: '#cfcfcf', oculta: '#eceff2',
  d3: '#2171b5', d2: '#6baed6', d1: '#bdd7e7', cero: '#f0f0f0',
  b4: '#54278f', b3: '#756bb1', b2: '#9e9ac8', b1: '#cbc9e2', b0: '#f2f0f7',
};
const SEM = { 0: 'nd', 1: 'bajo', 2: 'medio', 3: 'alto' };
export const NIVEL = { alto: 'Alta', medio: 'Media', bajo: 'Baja', nd: 'Sin dato' };
export const nivelDe = cod => SEM[cod];

export const escalaDe = vista => (vista === 'dif' ? 'dif' : vista === 'brecha' ? 'brecha' : 'sem');
export const escala = () => escalaDe(vistaActiva());

// cortes de la vista 3: terciles de las reducciones positivas del escenario elegido
export let difCortes = [0, 0];
export function recalcular() {
  const reds = [];
  for (const d of Object.values(datos.DATA.municipios)) {
    const r = escenario(d)[2];
    if (r > 0) reds.push(r);
  }
  reds.sort((a, b) => a - b);
  const q = p => reds[Math.min(reds.length - 1, Math.floor(p * reds.length))];
  difCortes = reds.length ? [q(1 / 3), q(2 / 3)] : [0, 0];
}

export function categoria(vista, d) {
  if (!d) return 'nd';
  switch (vista) {
    case 'sin': case 'comparar': return SEM[d.cs];
    case 'con': return SEM[escenario(d)[1]];
    case 'dif': {
      const r = escenario(d)[2];
      if (!(r > 0)) return 'cero';
      return r < difCortes[0] ? 'd1' : r < difCortes[1] ? 'd2' : 'd3';
    }
    case 'brecha': {
      if (d.br == null) return 'nd';
      const c = datos.DATA.meta.brecha_cortes;
      let i = 0;
      while (i < c.length && d.br >= c[i]) i++;
      return 'b' + i;
    }
  }
  return 'nd';
}

// filas de la leyenda de cada escala, de mayor a menor (rangos redondeados; el valor exacto va en la ficha)
export function categoriasDe(esc) {
  const m = datos.DATA.meta;
  const ent = x => Math.round(x);
  const f1 = x => x.toLocaleString('es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (esc === 'sem') {
    return [
      { cat: 'alto', nombre: 'Alta', rango: `${ent(m.corte_rojo)}% o más` },
      { cat: 'medio', nombre: 'Media', rango: `${ent(m.corte_amarillo)}% a ${ent(m.corte_rojo)}%` },
      { cat: 'bajo', nombre: 'Baja', rango: `menos de ${ent(m.corte_amarillo)}%` },
      { cat: 'nd', nombre: 'Sin dato', rango: '' },
    ];
  }
  if (esc === 'dif') {
    const [c1, c2] = difCortes.map(f1);
    return [
      { cat: 'd3', nombre: 'Baja mucho', rango: `${c2} puntos o más` },
      { cat: 'd2', nombre: 'Baja', rango: `${c1} a ${c2} puntos` },
      { cat: 'd1', nombre: 'Baja poco', rango: `menos de ${c1} puntos` },
      { cat: 'cero', nombre: 'No cambia', rango: 'no está en rojo' },
    ];
  }
  const c = m.brecha_cortes.map(ent);
  return [
    { cat: 'b4', nombre: 'Muy grande', rango: `${c[3]} puntos o más` },
    { cat: 'b3', nombre: 'Grande', rango: `${c[2]} a ${c[3]} puntos` },
    { cat: 'b2', nombre: 'Media', rango: `${c[1]} a ${c[2]} puntos` },
    { cat: 'b1', nombre: 'Pequeña', rango: `${c[0]} a ${c[1]} puntos` },
    { cat: 'b0', nombre: 'Muy pequeña', rango: `menos de ${c[0]} puntos` },
    { cat: 'nd', nombre: 'Sin dato', rango: '' },
  ];
}

// cuantos municipios hay en cada categoria de la vista (los mismos que pinta el mapa)
export function conteos(vista) {
  const n = {};
  for (const d of Object.values(datos.DATA.municipios)) {
    const c = categoria(vista, d);
    n[c] = (n[c] || 0) + 1;
  }
  return n;
}

export const esFragil = d => d && d.av.length > 0;

// ---------- URL ----------
const VALIDOS = {
  vista: ['sin', 'con', 'dif', 'brecha'], grupo: ['jovenes', 'hombres', 'rural'], efecto: ['5', '10', '15'],
  comparar: ['lado', 'cortina'], panel: ['mapa', 'lista'],
};

export function leerURL() {
  const p = new URLSearchParams(location.hash.slice(1));
  for (const [k, ok] of Object.entries(VALIDOS)) {
    if (ok.includes(p.get(k))) estado[k] = p.get(k);
  }
  const mun = p.get('mun');
  if (mun && datos.DATA.municipios[mun]) estado.mun = mun;
  if (/^\d{2}$/.test(p.get('edo') || '')) estado.edo = p.get('edo');
  if (p.get('ocultas')) estado.ocultas = new Set(p.get('ocultas').split(','));
  estado.fragiles = p.get('fragiles') === '1';
  estado.soloFragiles = p.get('sf') === '1';
  if (p.get('orden')) estado.orden = p.get('orden');
}

export function escribirURL() {
  const p = new URLSearchParams();
  p.set('vista', estado.vista);
  p.set('grupo', estado.grupo);
  p.set('efecto', estado.efecto);
  if (estado.comparar) p.set('comparar', estado.comparar);
  if (estado.mun) p.set('mun', estado.mun);
  if (estado.ocultas.size) p.set('ocultas', [...estado.ocultas].join(','));
  if (estado.fragiles) p.set('fragiles', '1');
  if (estado.panel !== 'mapa') p.set('panel', estado.panel);
  if (estado.edo) p.set('edo', estado.edo);
  if (estado.soloFragiles) p.set('sf', '1');
  if (estado.orden) p.set('orden', estado.orden);
  history.replaceState(null, '', '#' + p.toString());
}
