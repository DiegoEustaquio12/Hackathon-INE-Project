// compartir y exportar: copiar enlace, imagen PNG del mapa, CSV e impresion
import {
  datos, estado, vistaActiva, vistaMapa, escala, categoria, categoriasDe, conteos, cambioColor, esFragil, COLORES, escribirURL,
} from './estado.js';
import { VISTAS, GRUPOS, nombreEstado } from './textos.js';
import { entero, pct, descargar, avisar } from './util.js';
import { descargarCSV } from './lista.js';

export async function copiarEnlace() {
  escribirURL();
  try {
    await navigator.clipboard.writeText(location.href);
    avisar('Enlace copiado');
  } catch {
    window.prompt('Copia este enlace:', location.href);
  }
}

export { descargarCSV };

// se imprime la misma imagen que se descarga: el mapa en vivo no se reacomoda bien al tamaño de la hoja
export async function imprimir() {
  const { cv } = await componerImagen('hoja');
  const hoja = document.getElementById('hoja-impresion');
  hoja.innerHTML = `<img alt="Mapa para imprimir" src="${cv.toDataURL('image/png')}">`;
  await hoja.querySelector('img').decode();
  window.print();
}
window.addEventListener('afterprint', () => { document.getElementById('hoja-impresion').innerHTML = ''; });

// ---------- imagen PNG ----------
const FUENTE = 'system-ui, -apple-system, "Segoe UI", sans-serif';

function partirTexto(ctx, texto, ancho) {
  const lineas = [];
  let linea = '';
  for (const p of texto.split(' ')) {
    const prueba = linea ? `${linea} ${p}` : p;
    if (ctx.measureText(prueba).width > ancho && linea) { lineas.push(linea); linea = p; } else linea = prueba;
  }
  if (linea) lineas.push(linea);
  return lineas;
}

// ---------- mapa dibujado desde los poligonos (nitido y a la escala de la hoja) ----------
const merc = ([lon, lat]) => [lon, -Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) * (180 / Math.PI)];
const anillos = g => (g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : []);

let limites;
function limitesMexico() {
  if (limites) return limites;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of datos.GEO.features) {
    for (const pol of anillos(f.geometry)) for (const p of pol[0]) {
      const [x, y] = merc(p);
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
  }
  limites = [x0, y0, x1, y1];
  return limites;
}

function trazar(ctx, geom, aPx) {
  ctx.beginPath();
  for (const pol of anillos(geom)) {
    for (const anillo of pol) {
      anillo.forEach((p, i) => { const [x, y] = aPx(p); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
      ctx.closePath();
    }
  }
}

function dibujarMapa(ctx, cual, x, y, w, h) {
  const [x0, y0, x1, y1] = limitesMexico();
  const esc = Math.min(w / (x1 - x0), h / (y1 - y0)) * 0.97;
  const dx = x + (w - (x1 - x0) * esc) / 2, dy = y + (h - (y1 - y0) * esc) / 2;
  const aPx = p => { const [mx, my] = merc(p); return [dx + (mx - x0) * esc, dy + (my - y0) * esc]; };
  const vista = vistaMapa(cual);

  ctx.save();
  ctx.fillStyle = '#eef2f6';
  ctx.fillRect(x, y, w, h);
  ctx.lineJoin = 'round';
  const resaltar = [];
  for (const f of datos.GEO.features) {
    const clave = f.properties.CVEGEO;
    const d = datos.DATA.municipios[clave];
    const cat = categoria(vista, d);
    const oculta = estado.ocultas.has(cat);
    trazar(ctx, f.geometry, aPx);
    ctx.fillStyle = oculta ? COLORES.oculta : COLORES[cat];
    ctx.fill('evenodd');
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 0.35;
    ctx.stroke();
    if (oculta) continue;
    if (clave === estado.mun) resaltar.push([f, 'sel']);
    else if (estado.fragiles && esFragil(d)) resaltar.push([f, 'fragil']);
    else if (vista === 'con' && d && cambioColor(d)) resaltar.push([f, 'cambio']);
  }
  if (datos.ESTADOS) {
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 0.9;
    for (const f of datos.ESTADOS.features) { trazar(ctx, f.geometry, aPx); ctx.stroke(); }
  }
  // contornos encima: cambia de color, poco confiable y el municipio elegido al final
  const orden = { cambio: 0, fragil: 1, sel: 2 };
  resaltar.sort((a, b) => orden[a[1]] - orden[b[1]]);
  for (const [f, tipo] of resaltar) {
    trazar(ctx, f.geometry, aPx);
    ctx.setLineDash(tipo === 'fragil' ? [4, 3] : []);
    ctx.strokeStyle = '#0b1220';
    ctx.lineWidth = tipo === 'sel' ? 3 : 1.4;
    ctx.stroke();
  }
  ctx.setLineDash([]);
  ctx.restore();
}

// hoja completa: titulo, que muestra, mapa(s), leyenda y fuente.
// formato 'hoja' = carta horizontal para imprimir; 'imagen' = 16:9 para diapositivas
async function componerImagen(formato = 'imagen') {
  const vista = vistaActiva();
  const conEscenario = vista !== 'sin' && vista !== 'brecha';
  const [W, H] = formato === 'hoja' ? [1320, 1000] : [1600, 900];
  const k = 2, pad = 44, anchoLey = 310;
  const cv = document.createElement('canvas');
  cv.width = W * k;
  cv.height = H * k;
  const ctx = cv.getContext('2d');
  ctx.scale(k, k);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);
  ctx.textBaseline = 'alphabetic';

  // titulo y que muestra
  const titulo = `Abstención 2027 por municipio · ${vista === 'comparar' ? 'sin y con intervención' : VISTAS[vista].corto.toLowerCase()}`;
  ctx.fillStyle = '#0f172a';
  ctx.font = `700 32px ${FUENTE}`;
  ctx.fillText(titulo, pad, pad + 26);
  const que = vista === 'comparar' ? 'Izquierda: sin intervención. Derecha: con intervención.' : VISTAS[vista].que;
  const sub = conEscenario ? `${que} Intervención: ${GRUPOS[estado.grupo].nombre}, efecto supuesto de ${estado.efecto}%.` : que;
  ctx.font = `18px ${FUENTE}`;
  ctx.fillStyle = '#475569';
  const lineasSub = partirTexto(ctx, sub, W - pad * 2).slice(0, 2);
  lineasSub.forEach((l, i) => ctx.fillText(l, pad, pad + 62 + i * 25));
  const arriba = pad + 62 + lineasSub.length * 25 + 12;
  const abajo = H - pad - 34;

  // mapa(s)
  const mx = pad, mw = W - pad * 2 - anchoLey - 28, mh = abajo - arriba;
  const cuales = estado.comparar ? ['A', 'B'] : ['A'];
  const sep = 14, w1 = (mw - (cuales.length - 1) * sep) / cuales.length;
  cuales.forEach((c, i) => {
    const x = mx + i * (w1 + sep);
    dibujarMapa(ctx, c, x, arriba, w1, mh);
    if (estado.comparar) {
      ctx.font = `600 17px ${FUENTE}`;
      ctx.fillStyle = '#0f172a';
      ctx.fillText(c === 'B' ? VISTAS.con.corto : VISTAS.sin.corto, x + 12, arriba + 28);
    }
  });

  // leyenda
  const lx = W - pad - anchoLey;
  let ly = arriba + 6;
  const n = conteos(vista);
  const nCon = vista === 'comparar' ? conteos('con') : null;
  ctx.fillStyle = '#0f172a';
  ctx.font = `700 19px ${FUENTE}`;
  ctx.fillText(document.querySelector('.leyenda-titulo b')?.textContent || 'Leyenda', lx, ly + 18);
  ly += 40;
  for (const c of categoriasDe(escala())) {
    if (c.cat === 'nd' && !n.nd) continue;
    ctx.fillStyle = estado.ocultas.has(c.cat) ? COLORES.oculta : COLORES[c.cat];
    ctx.fillRect(lx, ly, 24, 24);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 1;
    ctx.strokeRect(lx + 0.5, ly + 0.5, 23, 23);
    ctx.fillStyle = '#0f172a';
    ctx.font = `600 18px ${FUENTE}`;
    ctx.fillText(c.nombre, lx + 36, ly + 18);
    const anchoNombre = ctx.measureText(c.nombre + '  ').width;
    ctx.font = `17px ${FUENTE}`;
    ctx.fillStyle = '#334155';
    if (c.rango) ctx.fillText(c.rango, lx + 36 + anchoNombre, ly + 18);
    ctx.fillStyle = '#64748b';
    ctx.font = `15px ${FUENTE}`;
    const cuenta = nCon ? `${entero(n[c.cat] || 0)} → ${entero(nCon[c.cat] || 0)}` : entero(n[c.cat] || 0);
    ctx.fillText(`${cuenta} municipios`, lx + 36, ly + 40);
    ly += 60;
  }
  const marca = (texto, discontinua) => {
    ctx.setLineDash(discontinua ? [4, 3] : []);
    ctx.strokeStyle = '#0b1220';
    ctx.lineWidth = 2;
    ctx.strokeRect(lx + 2, ly + 2, 20, 20);
    ctx.setLineDash([]);
    ctx.fillStyle = '#0f172a';
    ctx.font = `17px ${FUENTE}`;
    ctx.fillText(texto, lx + 36, ly + 18);
    ly += 34;
  };
  if (vista === 'con' || vista === 'comparar') marca('Cambia de color', false);
  if (estado.fragiles) marca('Dato poco confiable', true);
  if (estado.mun) {
    const d = datos.DATA.municipios[estado.mun];
    ly += 10;
    ctx.fillStyle = '#0f172a';
    ctx.font = `700 17px ${FUENTE}`;
    ctx.fillText('Municipio resaltado', lx, ly + 16);
    ctx.font = `17px ${FUENTE}`;
    partirTexto(ctx, `${d.n}, ${nombreEstado(d.e)}: ${pct(d.p)} de abstención prevista.`, anchoLey)
      .forEach((l, i) => ctx.fillText(l, lx, ly + 42 + i * 23));
  }

  // pie: fuente, fecha y aviso del supuesto
  ctx.font = `14px ${FUENTE}`;
  ctx.fillStyle = '#475569';
  const fecha = new Date().toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
  const aviso = conEscenario ? ' La intervención es hipotética: su efecto es un supuesto, no una medición.' : '';
  partirTexto(ctx, `Datos: CCPC INE 2009–2024 · Predicción del equipo · ${fecha}. El color compara a cada municipio con el resto del país.${aviso}`, W - pad * 2)
    .slice(0, 2).forEach((l, i) => ctx.fillText(l, pad, abajo + 24 + i * 19));

  const nombre = `abstencion_2027_${vista === 'comparar' ? 'comparacion' : 'mapa' + VISTAS[vista].num}${conEscenario ? `_${estado.grupo}_${estado.efecto}` : ''}.png`;
  return { cv, nombre };
}

export async function descargarPNG() {
  const { cv, nombre } = await componerImagen();
  cv.toBlob(b => { descargar(b, nombre); avisar('Imagen descargada'); }, 'image/png');
}

// el menu Compartir y el menu ⋯ usan las mismas acciones
export const ACCIONES = {
  enlace: copiarEnlace,
  png: descargarPNG,
  csv: descargarCSV,
  imprimir,
};
