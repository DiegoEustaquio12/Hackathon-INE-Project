// mapas Leaflet: estilos, seleccion, contornos, limites estatales, comparacion y cortina
import {
  datos, estado, cambiar, vistaMapa, categoria, COLORES, NIVEL, nivelDe, escenario, cambioColor, esFragil,
} from './estado.js';
import { VISTAS, nombreEstado } from './textos.js';
import { esc, pct, puntos, $ } from './util.js';

export const mapas = {};
const sinMovimiento = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- estilo de cada municipio ----------
function estiloDe(obj) {
  return f => {
    const clave = f.properties.CVEGEO;
    const d = datos.DATA.municipios[clave];
    const vista = vistaMapa(obj.cual);
    const cat = categoria(vista, d);
    const oculta = estado.ocultas.has(cat);
    const s = {
      fillColor: oculta ? COLORES.oculta : COLORES[cat], fillOpacity: oculta ? 0.7 : 0.88,
      color: '#ffffff', weight: 0.3, dashArray: null,
    };
    if (clave === estado.mun) return { ...s, color: '#0b1220', weight: 3.2 };
    if (oculta) return s;
    if (estado.fragiles && esFragil(d)) return { ...s, color: '#1f2937', weight: 1.4, dashArray: '4 3' };
    if (vista === 'con' && d && cambioColor(d)) return { ...s, color: '#1f2937', weight: 1.6 };
    return s;
  };
}

// texto breve al pasar el cursor
function etiqueta(obj, clave) {
  const d = datos.DATA.municipios[clave];
  const f = obj.capas[clave].feature.properties;
  if (!d) return `<b>${esc(f.NOMGEO)}</b><br>Sin datos`;
  const lugar = `<b>${esc(d.n)}</b>, ${esc(nombreEstado(d.e))}`;
  const vista = vistaMapa(obj.cual);
  let txt;
  if (vista === 'sin') txt = d.cs ? `Abstención ${NIVEL[nivelDe(d.cs)].toLowerCase()} · ${pct(d.p)}` : 'Sin dato';
  else if (vista === 'con') {
    const [con, col] = escenario(d);
    txt = d.cs ? `Con intervención: ${NIVEL[nivelDe(col)].toLowerCase()} · ${pct(con)}` : 'Sin dato';
  } else if (vista === 'dif') {
    const r = escenario(d)[2];
    txt = r > 0 ? `Baja ${puntos(r)}` : 'No cambia';
  } else txt = d.br == null ? 'Sin dato' : `${puntos(d.br)} más en intermedias`;
  return `${lugar}<br>${txt}`;
}

// ---------- sincronizacion de los dos mapas ----------
// solo manda el ultimo mapa que tocó la persona; asi no hay ida y vuelta entre los dos
let lider = null;
const tocar = m => () => { lider = m; };

export function alinear() {
  const { A, B } = mapas;
  if (!A || !B || !estado.comparar) return;
  lider = A.map;
  B.map.setView(A.map.getCenter(), A.map.getZoom(), { animate: false });
}

function sincronizar(a, b) {
  lider = a;
  for (const m of [a, b]) {
    const c = m.getContainer();
    for (const ev of ['pointerdown', 'mousedown', 'touchstart', 'wheel', 'dblclick']) {
      c.addEventListener(ev, tocar(m), { passive: true, capture: true });
    }
    // moveend y zoomend cierran el ultimo pixel que deja la inercia del arrastre
    m.on('move zoom moveend zoomend', () => {
      if (!estado.comparar || lider !== m) return;
      const otro = m === a ? b : a;
      otro.setView(m.getCenter(), m.getZoom(), { animate: false });
    });
  }
}

// al comparar, el zoom no se anima: los dos mapas cambian en el mismo cuadro
// (_zoomAnimated es interno de Leaflet; es seguro porque usamos la copia fija 1.9.4 de vendor/)
function animarZoom(si) {
  for (const o of Object.values(mapas)) {
    o.map._zoomAnimated = si && o.zoomAnimable;
    o.map.options.zoomAnimation = si && o.zoomAnimable;
  }
}

// ---------- crear un mapa ----------
export function crearMapa(divId, cual) {
  const map = L.map(divId, { preferCanvas: true, zoomSnap: 0.25, zoomControl: false, attributionControl: false })
    .setView([23.6, -102.5], 5);
  // el mapa B nunca se encuadra por su cuenta: siempre copia al A
  const obj = { map, cual, capas: {}, encuadrado: cual === 'B', zoomAnimable: map._zoomAnimated };
  obj.estilo = estiloDe(obj);

  L.control.zoom({ position: 'topleft', zoomInTitle: 'Acercar', zoomOutTitle: 'Alejar' }).addTo(map);
  const inicio = L.control({ position: 'topleft' });
  inicio.onAdd = () => {
    const b = L.DomUtil.create('button', 'boton-inicio');
    b.type = 'button';
    b.title = 'Ver todo México';
    b.setAttribute('aria-label', 'Ver todo México');
    b.innerHTML = '<span aria-hidden="true">⌂</span>';
    L.DomEvent.disableClickPropagation(b);
    b.addEventListener('click', verTodo);
    return b;
  };
  inicio.addTo(map);

  obj.layer = L.geoJSON(datos.GEO, {
    style: obj.estilo,
    onEachFeature: (f, l) => {
      const clave = f.properties.CVEGEO;
      obj.capas[clave] = l;
      l.bindTooltip(() => etiqueta(obj, clave), { sticky: true, direction: 'top', offset: [0, -8], className: 'etiqueta' });
      l.on('mouseover', () => { if (clave !== estado.mun) l.setStyle({ weight: 2, color: '#0b1220', dashArray: null }); });
      l.on('mouseout', () => l.setStyle(obj.estilo(f)));
      l.on('click', e => {
        L.DomEvent.stopPropagation(e);
        if (datos.DATA.municipios[clave]) cambiar({ mun: estado.mun === clave ? null : clave });
      });
    },
  }).addTo(map);
  obj.layer.on('tooltipopen', e => { obj.etiqueta = e.tooltip; });

  if (datos.ESTADOS) {
    L.geoJSON(datos.ESTADOS, { style: { color: '#334155', weight: 1.1, opacity: 0.8, fill: false }, interactive: false }).addTo(map);
  }

  // clic fuera de los municipios: quita la seleccion
  map.on('click', () => { if (estado.mun) cambiar({ mun: null }); });

  // si el contenedor cambia de tamaño (o empezo sin tamaño) se ajusta y se vuelve a alinear con el otro mapa
  new ResizeObserver(() => {
    const s = map.getContainer().getBoundingClientRect();
    if (!s.width || !s.height) return;
    map.invalidateSize({ animate: false });
    if (!obj.encuadrado) {
      // primer encuadre (p. ej. al venir de la lista): si hay municipio elegido, se va a el
      const destino = estado.mun && obj.capas[estado.mun] ? obj.capas[estado.mun].getBounds() : obj.layer.getBounds();
      map.fitBounds(destino, { animate: false, ...(estado.mun ? { maxZoom: 9, padding: [60, 60] } : {}) });
      obj.encuadrado = true;
    }
    requestAnimationFrame(alinear);
  }).observe(map.getContainer());

  mapas[cual] = obj;
  return obj;
}

// ---------- acciones ----------
export function cerrarEtiquetas() {
  for (const o of Object.values(mapas)) if (o.etiqueta) o.map.closeTooltip(o.etiqueta);
}

export function refrescarMapas() {
  for (const o of Object.values(mapas)) {
    o.layer.setStyle(o.estilo);
    if (estado.mun && o.capas[estado.mun]) o.capas[estado.mun].bringToFront();
  }
  $('#tituloA').textContent = estado.comparar ? VISTAS.sin.corto : '';
  $('#tituloB').textContent = estado.comparar ? VISTAS.con.corto : '';
  $('#tituloA').hidden = !estado.comparar;
}

export function verTodo() {
  const o = mapas.A;
  if (!o) return;
  lider = o.map;
  o.map.fitBounds(o.layer.getBounds(), { animate: !sinMovimiento() && !estado.comparar });
}

export function zoomMunicipio(clave) {
  const o = mapas.A;
  if (!o || !o.capas[clave]) return;
  lider = o.map;
  o.map.fitBounds(o.capas[clave].getBounds(), { maxZoom: 9, padding: [60, 60], animate: !sinMovimiento() && !estado.comparar });
}

export function zoomEstado(cve) {
  const o = mapas.A;
  if (!o) return;
  const b = L.latLngBounds([]);
  for (const [clave, capa] of Object.entries(o.capas)) if (clave.startsWith(cve)) b.extend(capa.getBounds());
  lider = o.map;
  if (b.isValid()) o.map.fitBounds(b, { padding: [30, 30], animate: !sinMovimiento() && !estado.comparar });
}

// ---------- comparacion: lado a lado o cortina ----------
let corte = 50;
export function aplicarComparacion() {
  const cont = $('#mapas');
  cont.classList.toggle('lado', estado.comparar === 'lado');
  cont.classList.toggle('cortina', estado.comparar === 'cortina');
  $('#contB').hidden = !estado.comparar;
  $('#cortina-barra').hidden = estado.comparar !== 'cortina';
  if (estado.comparar && !mapas.B) {
    crearMapa('mapaB', 'B');
    sincronizar(mapas.A.map, mapas.B.map);
  }
  animarZoom(!estado.comparar);
  moverCortina(corte);
  for (const o of Object.values(mapas)) o.map.invalidateSize({ animate: false });
  alinear();
}

function moverCortina(v) {
  corte = Math.max(0, Math.min(100, v));
  $('#mapas').style.setProperty('--corte', corte + '%');
  const barra = $('#cortina-barra');
  barra.setAttribute('aria-valuenow', Math.round(corte));
  barra.setAttribute('aria-valuetext', `${Math.round(corte)}% sin intervención a la izquierda`);
}

export function prepararCortina() {
  const barra = $('#cortina-barra');
  const cont = $('#mapas');
  const desdePuntero = e => {
    const r = cont.getBoundingClientRect();
    moverCortina(((e.clientX - r.left) / r.width) * 100);
  };
  barra.addEventListener('pointerdown', e => {
    barra.setPointerCapture(e.pointerId);
    barra.classList.add('arrastrando');
    desdePuntero(e);
  });
  barra.addEventListener('pointermove', e => { if (barra.hasPointerCapture(e.pointerId)) desdePuntero(e); });
  barra.addEventListener('pointerup', () => barra.classList.remove('arrastrando'));
  barra.addEventListener('keydown', e => {
    const pasos = { ArrowLeft: -5, ArrowDown: -5, ArrowRight: 5, ArrowUp: 5 };
    if (e.key in pasos) moverCortina(corte + pasos[e.key]);
    else if (e.key === 'Home') moverCortina(0);
    else if (e.key === 'End') moverCortina(100);
    else return;
    e.preventDefault();
  });
}
