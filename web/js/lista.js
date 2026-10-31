// lista de municipios prioritarios: filtros, orden, paginas de 50 y CSV
import {
  datos, estado, cambiar, vistaActiva, escenario, cambioColor, categoria, categoriasDe, escala, COLORES, NIVEL, nivelDe, esFragil,
} from './estado.js';
import { VISTAS, nombreEstado } from './textos.js';
import { esc, pct, puntos, entero, normalizar, descargar, $ } from './util.js';
import { recordar } from './buscador.js';
import { zoomMunicipio } from './mapa.js';

const PAGINA = 50;
let mostrar = PAGINA;
let texto = '';

const insignia = cod => `<span class="insignia ${nivelDe(cod)}">${cod ? NIVEL[nivelDe(cod)] : 'Sin dato'}</span>`;
const personasRed = d => (d.ln == null ? null : escenario(d)[2] / 100 * d.ln);

// columnas de cada vista: valor (para ordenar y CSV) y celda (para mostrar)
function columnas(vista) {
  const muni = { id: 'muni', titulo: 'Municipio', texto: true, valor: d => d.n, celda: () => '' };
  const ln = { id: 'ln', titulo: 'Lista nominal', valor: d => d.ln, celda: d => entero(d.ln) };
  const fragil = { id: 'fragil', titulo: '⚠', titulo_csv: 'datos_poco_confiables', valor: d => d.av.join('; '), celda: d => (esFragil(d) ? '<span title="Dato poco confiable" aria-label="Dato poco confiable">⚠</span>' : '') };
  const riesgoSin = { id: 'sin', titulo: 'Abstención prevista', valor: d => (d.cs ? d.p : null), celda: d => `${insignia(d.cs)} ${d.cs ? pct(d.p) : ''}` };
  const riesgoCon = { id: 'con', titulo: 'Con intervención', valor: d => (d.cs ? escenario(d)[0] : null), celda: d => (d.cs ? `${insignia(escenario(d)[1])} ${pct(escenario(d)[0])}` : insignia(0)) };
  const cambia = { id: 'cambia', titulo: '¿Cambia de color?', valor: d => (cambioColor(d) ? 1 : 0), celda: d => (cambioColor(d) ? 'Sí' : '—') };
  const red = { id: 'red', titulo: 'Puntos que baja', valor: d => escenario(d)[2], celda: d => (escenario(d)[2] > 0 ? puntos(escenario(d)[2]) : '—') };
  const gente = { id: 'gente', entero: true, titulo: 'Personas que votarían', valor: personasRed, celda: d => (personasRed(d) > 0 ? `≈ ${entero(personasRed(d))}` : '—') };
  const brecha = { id: 'br', titulo: 'Puntos más en intermedias', valor: d => d.br, celda: d => puntos(d.br) };
  const propias = {
    sin: [riesgoSin], con: [riesgoCon, cambia], dif: [red, gente], brecha: [brecha], comparar: [riesgoSin, riesgoCon, cambia],
  }[vista];
  return [muni, ...propias, ln, fragil];
}
const ORDEN_DEFECTO = { sin: 'sin:desc', con: 'con:desc', dif: 'gente:desc', brecha: 'br:desc', comparar: 'sin:desc' };

export function filasFiltradas() {
  const vista = vistaActiva();
  const vistaCat = vista === 'comparar' ? 'sin' : vista;
  const cols = columnas(vista);
  const [id, dir] = (estado.orden || ORDEN_DEFECTO[vista]).split(':');
  const col = cols.find(c => c.id === id) || cols.find(c => c.id === ORDEN_DEFECTO[vista].split(':')[0]);
  const t = normalizar(texto);
  const filas = Object.entries(datos.DATA.municipios).filter(([clave, d]) =>
    (!estado.edo || clave.startsWith(estado.edo))
    && !estado.ocultas.has(categoria(vistaCat, d))
    && (!estado.soloFragiles || esFragil(d))
    && (!t || normalizar(d.n).includes(t)));
  const signo = dir === 'asc' ? 1 : -1;
  filas.sort(([, a], [, b]) => {
    const va = col.valor(a), vb = col.valor(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;     // sin dato siempre al final
    if (vb == null) return -1;
    return (col.texto ? String(va).localeCompare(String(vb), 'es') : va - vb) * signo;
  });
  return { filas, cols, col, dir };
}

export function dibujarLista() {
  if (estado.panel !== 'lista') return;
  const vista = vistaActiva();
  const { filas, cols, col, dir } = filasFiltradas();
  const nombreVista = vista === 'comparar' ? 'Comparación sin y con intervención' : `Mapa ${VISTAS[vista].num}, ${VISTAS[vista].corto.toLowerCase()}`;

  $('#lista-titulo').textContent = `Municipios ordenados por ${col.titulo.toLowerCase()} · ${nombreVista}`;
  $('#lista-cuenta').textContent = filas.length
    ? `Mostrando ${entero(Math.min(mostrar, filas.length))} de ${entero(filas.length)}`
    : '';

  // filtros sincronizados con el estado
  $('#lista-edo').value = estado.edo;
  $('#lista-fragiles').checked = estado.soloFragiles;
  $('#lista-cats').innerHTML = categoriasDe(escala()).map(c => `<button type="button" class="chip" data-cat="${c.cat}"
      aria-pressed="${!estado.ocultas.has(c.cat)}"><i class="muestra" style="background:${COLORES[c.cat]}"></i>${esc(c.nombre)}</button>`).join('');
  $('#lista-orden').innerHTML = cols.filter(c => c.id !== 'fragil').flatMap(c => [
    `<option value="${c.id}:desc" ${c === col && dir === 'desc' ? 'selected' : ''}>${esc(c.titulo)} ${c.texto ? '(Z–A)' : '(mayor a menor)'}</option>`,
    `<option value="${c.id}:asc" ${c === col && dir === 'asc' ? 'selected' : ''}>${esc(c.titulo)} ${c.texto ? '(A–Z)' : '(menor a mayor)'}</option>`,
  ]).join('');

  const cabeza = cols.map(c => {
    const orden = c === col ? (dir === 'asc' ? 'ascending' : 'descending') : 'none';
    const flecha = c === col ? (dir === 'asc' ? ' ↑' : ' ↓') : '';
    return `<th scope="col" aria-sort="${orden}" class="${c.texto ? '' : 'num'}">
      <button type="button" class="ordenar" data-col="${c.id}">${esc(c.titulo)}${flecha}</button></th>`;
  }).join('');

  const cuerpo = filas.slice(0, mostrar).map(([clave, d]) => `<tr class="${clave === estado.mun ? 'sel' : ''}">
      <th scope="row"><button type="button" class="nombre-fila" data-clave="${clave}">${esc(d.n)}</button>
        <small>${esc(nombreEstado(d.e))}</small></th>
      ${cols.slice(1).map(c => `<td class="${c.texto ? '' : 'num'}" data-titulo="${esc(c.titulo)}">${c.celda(d)}</td>`).join('')}
    </tr>`).join('');

  $('#tabla').innerHTML = `<caption class="solo-lector">${esc($('#lista-titulo').textContent)}</caption>
    <thead><tr>${cabeza}</tr></thead><tbody>${cuerpo}</tbody>`;
  $('#lista-vacia').hidden = filas.length > 0;
  $('#lista-mas').hidden = filas.length <= mostrar;
}

export function descargarCSV() {
  const { filas, cols } = filasFiltradas();
  const vista = vistaActiva();
  const encabezados = ['clave_inegi', 'municipio', 'estado', ...cols.slice(1).map(c => c.titulo_csv || c.titulo)];
  const campo = v => {
    if (v == null) return '';
    const s = typeof v === 'number' ? String(Math.round(v * 100) / 100) : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lineas = [encabezados.map(campo).join(',')]
    .concat(filas.map(([clave, d]) => [clave, d.n, nombreEstado(d.e),
      ...cols.slice(1).map(c => (c.entero && c.valor(d) != null ? Math.round(c.valor(d)) : c.valor(d)))].map(campo).join(',')));
  const escen = vista === 'sin' || vista === 'brecha' ? '' : `_${estado.grupo}_${estado.efecto}`;
  // BOM para que Excel respete los acentos
  descargar(new Blob(['﻿' + lineas.join('\r\n')], { type: 'text/csv;charset=utf-8' }),
    `riesgo_2027_${vista === 'comparar' ? 'comparacion' : 'vista' + VISTAS[vista].num}${escen}.csv`);
}

export function prepararLista() {
  const sel = $('#lista-edo');
  const edos = {};
  for (const [clave, d] of Object.entries(datos.DATA.municipios)) edos[clave.slice(0, 2)] = nombreEstado(d.e);
  sel.innerHTML = '<option value="">Todo el país</option>'
    + Object.entries(edos).sort((a, b) => a[1].localeCompare(b[1], 'es')).map(([c, n]) => `<option value="${c}">${esc(n)}</option>`).join('');

  const reiniciar = () => { mostrar = PAGINA; };
  sel.addEventListener('change', () => { reiniciar(); cambiar({ edo: sel.value }); });
  $('#lista-fragiles').addEventListener('change', e => { reiniciar(); cambiar({ soloFragiles: e.target.checked }); });
  $('#lista-texto').addEventListener('input', e => { texto = e.target.value; reiniciar(); dibujarLista(); });
  $('#lista-orden').addEventListener('change', e => cambiar({ orden: e.target.value }));
  $('#lista-mas-filtros-boton').addEventListener('click', e => {
    const abierto = $('#lista-mas-filtros').hidden;
    $('#lista-mas-filtros').hidden = !abierto;
    e.currentTarget.setAttribute('aria-expanded', String(abierto));
    e.currentTarget.textContent = abierto ? 'Menos filtros ▾' : 'Más filtros ▸';
  });
  $('#lista-mas').addEventListener('click', () => { mostrar += PAGINA; dibujarLista(); });
  $('#lista-csv').addEventListener('click', descargarCSV);
  $('#lista-quitar').addEventListener('click', () => {
    texto = '';
    $('#lista-texto').value = '';
    reiniciar();
    cambiar({ edo: '', soloFragiles: false, ocultas: new Set() });
  });
  $('#lista-cats').addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const ocultas = new Set(estado.ocultas);
    ocultas.has(chip.dataset.cat) ? ocultas.delete(chip.dataset.cat) : ocultas.add(chip.dataset.cat);
    reiniciar();
    cambiar({ ocultas });
    $(`#lista-cats .chip[data-cat="${chip.dataset.cat}"]`)?.focus();
  });
  $('#tabla').addEventListener('click', e => {
    const orden = e.target.closest('.ordenar');
    if (orden) {
      const { col, dir } = filasFiltradas();
      const id = orden.dataset.col;
      const nuevo = col.id === id ? (dir === 'desc' ? 'asc' : 'desc') : (id === 'muni' ? 'asc' : 'desc');
      cambiar({ orden: `${id}:${nuevo}` });
      $(`.ordenar[data-col="${id}"]`)?.focus();
      return;
    }
    // clic en un municipio: lleva al mapa, hace zoom y abre su ficha
    const fila = e.target.closest('.nombre-fila');
    if (fila) {
      const clave = fila.dataset.clave;
      recordar(clave);
      cambiar({ mun: clave, panel: 'mapa' });
      // espera a que el mapa vuelva a tener tamaño antes de acercarse
      setTimeout(() => zoomMunicipio(clave), 120);
    }
  });
}
