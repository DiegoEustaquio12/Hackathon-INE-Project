// buscador de municipios y estados (sin acentos, con teclado) y busquedas recientes
import { datos, estado, cambiar, COLORES, nivelDe } from './estado.js';
import { nombreEstado } from './textos.js';
import { esc, pct, entero, normalizar, almacen, $ } from './util.js';
import { zoomMunicipio, zoomEstado } from './mapa.js';
import { enfocarFicha } from './ficha.js';

const CLAVE_RECIENTES = 'abstencion2027.recientes';
let indice = [];
let recientes = almacen.leer(CLAVE_RECIENTES, []);
let opciones = [];
let activa = -1;

export function prepararBuscador() {
  const estados = {};
  for (const [clave, d] of Object.entries(datos.DATA.municipios)) {
    const edo = nombreEstado(d.e);
    indice.push({ tipo: 'mun', clave, nombre: d.n, edo, norm: normalizar(d.n), normTodo: normalizar(`${d.n} ${edo}`) });
    const cve = clave.slice(0, 2);
    (estados[cve] ||= { tipo: 'edo', clave: cve, nombre: edo, norm: normalizar(edo), n: 0 }).n++;
  }
  indice.push(...Object.values(estados));
  recientes = recientes.filter(c => datos.DATA.municipios[c]);

  const input = $('#buscar');
  input.addEventListener('input', () => mostrar(input.value));
  input.addEventListener('focus', () => mostrar(input.value));
  input.addEventListener('keydown', teclas);
  input.addEventListener('blur', () => setTimeout(cerrar, 150));
  $('#resultados').addEventListener('mousedown', e => e.preventDefault()); // no pierde el foco al hacer clic
  $('#resultados').addEventListener('click', e => {
    const li = e.target.closest('[data-i]');
    if (li) elegir(opciones[+li.dataset.i]);
    if (e.target.closest('.borrar-recientes')) {
      recientes = [];
      almacen.guardar(CLAVE_RECIENTES, recientes);
      mostrar('');
    }
  });
}

function buscar(q) {
  const n = normalizar(q);
  if (/^\d{2,5}$/.test(n)) {
    return indice.filter(x => x.tipo === 'mun' && x.clave.startsWith(n)).slice(0, 8);
  }
  const puntaje = x => {
    if (x.norm.startsWith(n)) return x.tipo === 'edo' ? 0 : 1;
    if (x.norm.split(/[\s-]+/).some(p => p.startsWith(n))) return 2;
    if (x.norm.includes(n)) return 3;
    if (x.normTodo && x.normTodo.includes(n)) return 4;
    return 9;
  };
  return indice.map(x => [puntaje(x), x]).filter(([p]) => p < 9)
    .sort((a, b) => a[0] - b[0] || a[1].nombre.localeCompare(b[1].nombre, 'es'))
    .slice(0, 8).map(([, x]) => x);
}

function filaHtml(x, i) {
  if (x.tipo === 'edo') {
    return `<li role="option" id="op-${i}" data-i="${i}" class="op">
      <span class="punto edo" aria-hidden="true">▦</span>
      <span class="op-texto"><b>${esc(x.nombre)}</b><small>Estado · ${entero(x.n)} municipios</small></span></li>`;
  }
  const d = datos.DATA.municipios[x.clave];
  const nivel = nivelDe(d.cs);
  return `<li role="option" id="op-${i}" data-i="${i}" class="op">
    <span class="punto" style="background:${COLORES[nivel]}" aria-hidden="true"></span>
    <span class="op-texto"><b>${esc(x.nombre)}</b><small>${esc(x.edo)}</small></span>
    <span class="op-valor">${d.cs ? pct(d.p) : 'Sin dato'}</span></li>`;
}

function mostrar(q) {
  const lista = $('#resultados');
  const input = $('#buscar');
  activa = -1;
  input.removeAttribute('aria-activedescendant');
  if (!q.trim()) {
    opciones = recientes.map(c => indice.find(x => x.tipo === 'mun' && x.clave === c)).filter(Boolean);
    if (!opciones.length) { cerrar(); return; }
    lista.innerHTML = `<li class="encabezado" role="presentation">Recientes
      <button type="button" class="enlace borrar-recientes" tabindex="-1">Borrar</button></li>`
      + opciones.map(filaHtml).join('');
  } else {
    opciones = buscar(q);
    lista.innerHTML = opciones.length
      ? opciones.map(filaHtml).join('')
      : `<li class="vacio" role="presentation">No encontramos «${esc(q)}». Revisa la ortografía o busca el estado.</li>`;
  }
  lista.hidden = false;
  input.setAttribute('aria-expanded', 'true');
}

function cerrar() {
  $('#resultados').hidden = true;
  $('#buscar').setAttribute('aria-expanded', 'false');
  $('#buscar').removeAttribute('aria-activedescendant');
  activa = -1;
}

function marcar(i) {
  activa = i;
  document.querySelectorAll('#resultados .op').forEach((li, j) => li.classList.toggle('activa', j === i));
  if (i >= 0) {
    $('#buscar').setAttribute('aria-activedescendant', `op-${i}`);
    document.getElementById(`op-${i}`)?.scrollIntoView({ block: 'nearest' });
  }
}

function teclas(e) {
  const abierta = !$('#resultados').hidden;
  if (e.key === 'ArrowDown') { e.preventDefault(); if (!abierta) mostrar(e.target.value); marcar(Math.min(opciones.length - 1, activa + 1)); }
  else if (e.key === 'ArrowUp') { e.preventDefault(); marcar(Math.max(0, activa - 1)); }
  else if (e.key === 'Enter') {
    const x = opciones[activa >= 0 ? activa : 0];
    if (x && abierta) { e.preventDefault(); elegir(x); }
  } else if (e.key === 'Escape') {
    e.stopPropagation();
    if (abierta) cerrar(); else { e.target.value = ''; e.target.blur(); }
  }
}

function elegir(x) {
  const input = $('#buscar');
  cerrar();
  if (x.tipo === 'edo') {
    input.value = x.nombre;
    if (estado.panel === 'lista') cambiar({ edo: x.clave });
    else zoomEstado(x.clave);
    return;
  }
  input.value = '';
  recientes = [x.clave, ...recientes.filter(c => c !== x.clave)].slice(0, 5);
  almacen.guardar(CLAVE_RECIENTES, recientes);
  cambiar({ mun: x.clave });
  if (estado.panel === 'mapa') zoomMunicipio(x.clave);
  enfocarFicha();
}

// tambien cuenta como reciente un municipio elegido en el mapa o en la lista
export function recordar(clave) {
  if (!clave || recientes[0] === clave) return;
  recientes = [clave, ...recientes.filter(c => c !== clave)].slice(0, 5);
  almacen.guardar(CLAVE_RECIENTES, recientes);
}
