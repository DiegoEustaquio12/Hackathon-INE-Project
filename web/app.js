'use strict';

// ---------- constantes ----------
const GRIS = '#cfcfcf';
const COLOR_SEM = { 0: GRIS, 1: '#2e9e5b', 2: '#f2c230', 3: '#d6453d' };
const NOMBRE_SEM = { 0: 'Sin clasificar', 1: 'Bajo', 2: 'Medio', 3: 'Alto' };
const BRECHA_COLORES = ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'];
const DIF_COLORES = ['#f0f0f0', '#bdd7e7', '#6baed6', '#2171b5'];
const INTERV = { jovenes: 'Jóvenes (18–34)', hombres: 'Hombres', rural: 'Zonas rurales' };
const INTERV_IDX = { jovenes: 0, hombres: 1, rural: 2 };

// ---------- estado ----------
let DATA, GEO;
const sel = { interv: 'jovenes', efecto: '10' };
let difCortes = [0, 0];
const mapas = [];

// ---------- utilidades ----------
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pts = v => (v == null ? '—' : v.toFixed(1) + '%');

// escenario elegido para un municipio: [abstencion con intervencion, color con intervencion, reduccion en puntos]
const escenario = d => d.esc[sel.interv][sel.efecto];
const cambioColor = d => d.cs !== 0 && escenario(d)[1] !== d.cs;

function tituloDe(modo) {
  const bases = {
    sin: '1 · Sin intervención',
    con: '2 · Con intervención',
    dif: '3 · Diferencia entre escenarios',
    brecha: '4 · Brecha intermedia vs presidencial',
  };
  const extra = (modo === 'con' || modo === 'dif') ? ` — ${INTERV[sel.interv]}, efecto ${sel.efecto}%` : '';
  return bases[modo] + extra;
}

// cortes de la escala del mapa 3: terciles de las reducciones positivas del escenario elegido
function recalcular() {
  const reds = [];
  for (const d of Object.values(DATA.municipios)) {
    const r = escenario(d)[2];
    if (r > 0) reds.push(r);
  }
  reds.sort((a, b) => a - b);
  const q = p => reds[Math.min(reds.length - 1, Math.floor(p * reds.length))];
  difCortes = reds.length ? [q(1 / 3), q(2 / 3)] : [0, 0];
}

// ---------- colores ----------
function color(modo, d) {
  if (!d) return GRIS;
  switch (modo) {
    case 'sin':
      return COLOR_SEM[d.cs];
    case 'con':
      return COLOR_SEM[escenario(d)[1]];
    case 'dif': {
      const r = escenario(d)[2];
      if (!(r > 0)) return DIF_COLORES[0];
      if (r < difCortes[0]) return DIF_COLORES[1];
      if (r < difCortes[1]) return DIF_COLORES[2];
      return DIF_COLORES[3];
    }
    case 'brecha': {
      if (d.br == null) return GRIS;
      const c = DATA.meta.brecha_cortes;
      let i = 0;
      while (i < c.length && d.br >= c[i]) i++;
      return BRECHA_COLORES[i];
    }
  }
  return GRIS;
}

function leyendaHtml(modo) {
  const fila = (c, t) => `<div><i style="background:${c}"></i>${t}</div>`;
  const m = DATA.meta;
  let h = `<b>${esc(tituloDe(modo))}</b>`;
  if (modo === 'sin' || modo === 'con') {
    h += fila(COLOR_SEM[3], `Alto (≥ ${m.corte_rojo} pts)`)
      + fila(COLOR_SEM[2], `Medio (${m.corte_amarillo}–${m.corte_rojo})`)
      + fila(COLOR_SEM[1], `Bajo (< ${m.corte_amarillo})`);
    if (modo === 'con') h += '<div><i class="borde"></i>Cambia de color</div>';
  } else if (modo === 'dif') {
    const [c1, c2] = difCortes.map(x => x.toFixed(1));
    h += fila(DIF_COLORES[3], `Baja ≥ ${c2} pts`)
      + fila(DIF_COLORES[2], `Baja ${c1}–${c2} pts`)
      + fila(DIF_COLORES[1], `Baja < ${c1} pts`)
      + fila(DIF_COLORES[0], 'Sin cambio');
  } else {
    const c = m.brecha_cortes;
    h += fila(BRECHA_COLORES[4], `≥ ${c[3]} pts`)
      + fila(BRECHA_COLORES[3], `${c[2]}–${c[3]}`)
      + fila(BRECHA_COLORES[2], `${c[1]}–${c[2]}`)
      + fila(BRECHA_COLORES[1], `${c[0]}–${c[1]}`)
      + fila(BRECHA_COLORES[0], `< ${c[0]}`);
  }
  return h + fila(GRIS, 'Sin dato / sin clasificar');
}

// ---------- mapas ----------
function estiloDe(obj) {
  return f => {
    const d = DATA.municipios[f.properties.CVEGEO];
    const marca = obj.modo === 'con' && d && cambioColor(d);
    return { fillColor: color(obj.modo, d), fillOpacity: 0.85, color: marca ? '#000' : '#fff', weight: marca ? 1.6 : 0.3 };
  };
}

function crearMapa(divId, tituloId, modo) {
  const map = L.map(divId, { preferCanvas: true, zoomSnap: 0.25 }).setView([23.6, -102.5], 5);
  const obj = { map, modo, tituloId };
  obj.estilo = estiloDe(obj);
  obj.layer = L.geoJSON(GEO, {
    style: obj.estilo,
    onEachFeature: (f, l) => {
      l.on('mouseover', () => { l.setStyle({ weight: 2, color: '#000' }); mostrarInfo(f); });
      l.on('mouseout', () => obj.layer.resetStyle(l));
    },
  }).addTo(map);
  map.fitBounds(obj.layer.getBounds());

  const ley = L.control({ position: 'bottomleft' });
  ley.onAdd = () => {
    obj.div = L.DomUtil.create('div', 'leyenda');
    obj.div.innerHTML = leyendaHtml(obj.modo);
    return obj.div;
  };
  ley.addTo(map);

  obj.refrescar = () => {
    obj.layer.setStyle(obj.estilo);
    obj.div.innerHTML = leyendaHtml(obj.modo);
    document.getElementById(obj.tituloId).textContent = tituloDe(obj.modo);
  };
  document.getElementById(tituloId).textContent = tituloDe(modo);
  mapas.push(obj);
  return obj;
}

// total nacional del escenario elegido (calculado en make_escenarios.py con todos los municipios)
function actualizarResumen() {
  const t = DATA.meta.totales[sel.interv][sel.efecto];
  const personas = t.personas >= 1e6
    ? `${(t.personas / 1e6).toFixed(2)} millones de personas`
    : `${t.personas.toLocaleString('es-MX')} personas`;
  document.getElementById('resumen').innerHTML =
    `<b>${esc(INTERV[sel.interv])}, efecto ${esc(sel.efecto)}%:</b> ≈ ${personas} dejarían de abstenerse `
    + `(−${t.pts.toFixed(2)} pts de abstención nacional)`;
}

function refrescarTodo() {
  recalcular();
  actualizarResumen();
  mapas.forEach(o => o.refrescar());
}

function sincronizar(a, b) {
  let ocupado = false;
  const seguir = (x, y) => x.on('move', () => {
    if (ocupado) return;
    ocupado = true;
    y.setView(x.getCenter(), x.getZoom(), { animate: false });
    ocupado = false;
  });
  seguir(a, b);
  seguir(b, a);
}

// ---------- panel de datos ----------
function mostrarInfo(f) {
  const el = document.getElementById('info');
  const d = DATA.municipios[f.properties.CVEGEO];
  if (!d) {
    el.innerHTML = `<h3>${esc(f.properties.NOMGEO)}</h3>Sin datos para este municipio.`;
    return;
  }
  const [con, colCon, red] = escenario(d);
  const i = INTERV_IDX[sel.interv];
  const gr = d.gr[i];
  const rango = d.min == null ? '' : ` <span style="color:#666">(rango ${d.min.toFixed(1)}–${d.max.toFixed(1)})</span>`;

  const filas = [
    ['Lista nominal', d.ln == null ? '—' : d.ln.toLocaleString('es-MX')],
    ['Sin intervención', `${pts(d.p)} · ${NOMBRE_SEM[d.cs]}${rango}`],
  ];
  let nota = '';
  if (d.cs === 3) {
    filas.push([`Con intervención`, `${pts(con)} · ${NOMBRE_SEM[colCon]}`]);
    filas.push(['Reducción', red > 0 ? `−${red.toFixed(2)} pts` : '0 pts']);
    if (red > 0 && d.ln != null) {
      filas.push(['Personas alcanzadas', `≈ ${Math.round(red / 100 * d.ln).toLocaleString('es-MX')}`]);
    }
    if (cambioColor(d)) filas.push(['Cambia de color', `Sí: ${NOMBRE_SEM[3]} → ${NOMBRE_SEM[colCon]}`]);
    if (!(red > 0)) {
      nota = gr === 0
        ? 'Sin efecto: ninguna persona de la lista pertenece al grupo objetivo.'
        : 'Sin efecto en este municipio.';
    }
  } else if (d.cs === 0) {
    nota = 'Sin clasificar: no hay datos de voto de la última elección, por eso no se le asigna color.';
  } else {
    nota = 'La intervención no se aplica: el municipio no está en rojo.';
  }
  if (gr != null) filas.push(['Grupo objetivo', `${gr.toFixed(1)}% de la lista`]);
  filas.push(['Brecha interm.–pres.', d.br == null ? '—' : d.br.toFixed(1) + ' pts']);

  const avisos = [...d.av];
  if (d.im[i] && d.cs === 3) avisos.push('grupo objetivo estimado (dato imputado)');

  el.innerHTML =
    `<h3>${esc(d.n)}</h3><div class="sub">${esc(d.e)}</div>`
    + (d.cs === 3 ? `<div class="sub">Escenario: ${esc(INTERV[sel.interv])}, efecto ${esc(sel.efecto)}%</div>` : '')
    + `<table>${filas.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('')}</table>`
    + (nota ? `<div class="nota">${esc(nota)}</div>` : '')
    + (d.rz.length ? `<div class="nota"><b>Por qué:</b><ul>${d.rz.map(r => `<li>${esc(r)}</li>`).join('')}</ul></div>` : '')
    + (avisos.length ? `<div class="aviso-dato">⚠ Dato frágil: ${avisos.map(esc).join(', ')}</div>` : '');
}

// ---------- arranque ----------
const leer = r => {
  if (!r.ok) throw new Error(`${r.url} → ${r.status}`);
  return r.json();
};

Promise.all([
  fetch('municipios_web.geojson').then(leer),
  fetch('escenarios.json').then(leer),
]).then(([geo, datos]) => {
  GEO = geo;
  DATA = datos;
  document.getElementById('aviso').textContent = DATA.meta.aviso;
  recalcular();
  actualizarResumen();

  const A = crearMapa('mapaA', 'tituloA', 'sin');
  let B = null;
  document.getElementById('cargando').remove();

  const botones = [...document.querySelectorAll('header button')];
  botones.forEach(b => b.addEventListener('click', () => {
    botones.forEach(x => x.classList.toggle('activo', x === b));
    A.modo = b.dataset.modo;
    A.refrescar();
  }));

  document.getElementById('sel-interv').addEventListener('change', e => { sel.interv = e.target.value; refrescarTodo(); });
  document.getElementById('sel-efecto').addEventListener('change', e => { sel.efecto = e.target.value; refrescarTodo(); });

  document.getElementById('comparar').addEventListener('change', e => {
    const on = e.target.checked;
    document.getElementById('contB').hidden = !on;
    botones.forEach(b => { b.disabled = on; });
    if (on) {
      A.modo = 'sin';
      A.map.invalidateSize();
      if (!B) {
        B = crearMapa('mapaB', 'tituloB', 'con');
        sincronizar(A.map, B.map);
      }
      B.modo = 'con';
      B.map.invalidateSize();
      B.map.setView(A.map.getCenter(), A.map.getZoom(), { animate: false });
      A.refrescar();
      B.refrescar();
    } else {
      A.map.invalidateSize();
      botones.forEach(x => x.classList.toggle('activo', x.dataset.modo === 'sin'));
      A.modo = 'sin';
      A.refrescar();
    }
  });
}).catch(err => {
  document.getElementById('cargando').innerHTML =
    'No se pudieron cargar los archivos.<br>Abre esta página con un servidor local (python3 -m http.server), no con doble clic.<br><small>' + esc(err) + '</small>';
});