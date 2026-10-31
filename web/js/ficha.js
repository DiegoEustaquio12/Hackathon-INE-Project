// ficha del municipio (solo existe si hay uno seleccionado) y resumen en texto de la vista
import {
  datos, estado, cambiar, escenario, grupoPct, vistaActiva, conteos, categoriasDe, escala,
  COLORES, NIVEL, nivelDe,
} from './estado.js';
import { GRUPOS, GRUPO_IDX, FRACCION, BANDERAS, VISTAS, nombreEstado, leerRazon } from './textos.js';
import { esc, pct, puntos, entero, personas, $, esMovil } from './util.js';
import { cerrarEtiquetas } from './mapa.js';

// rango del eje de la barra (se calcula una vez)
let eje;
function ejeBarra() {
  if (eje) return eje;
  let lo = Infinity, hi = -Infinity;
  for (const d of Object.values(datos.DATA.municipios)) {
    for (const v of [d.min, d.p, d.max]) if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
  }
  eje = [Math.floor(lo / 10) * 10, Math.ceil(hi / 10) * 10];
  return eje;
}

function barra(d) {
  const [lo, hi] = ejeBarra();
  const m = datos.DATA.meta;
  const x = v => ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * 100;
  const zona = (a, b, c) => `<span class="zona" style="left:${x(a)}%;width:${x(b) - x(a)}%;background:${c}"></span>`;
  const rango = d.min != null ? `<span class="rango" style="left:${x(d.min)}%;width:${x(d.max) - x(d.min)}%"></span>` : '';
  return `<div class="barra-riesgo" role="img"
      aria-label="Abstención prevista ${pct(d.p)}${d.min != null ? `, rango probable de ${pct(d.min)} a ${pct(d.max)}` : ''}">
      ${zona(lo, m.corte_amarillo, COLORES.bajo)}${zona(m.corte_amarillo, m.corte_rojo, COLORES.medio)}${zona(m.corte_rojo, hi, COLORES.alto)}
      ${rango}<span class="marcador" style="left:${x(d.p)}%"></span>
    </div>
    <div class="eje"><span style="left:${x(m.corte_amarillo)}%">${Math.round(m.corte_amarillo)}%</span>
      <span style="left:${x(m.corte_rojo)}%">${Math.round(m.corte_rojo)}%</span></div>
    ${d.min != null ? `<p class="nota">Rango probable: ${pct(d.min)} a ${pct(d.max)} (franja oscura).</p>` : ''}`;
}

const insignia = cod => `<span class="insignia ${nivelDe(cod)}">${cod ? `Abstención ${NIVEL[nivelDe(cod)].toLowerCase()}` : 'Sin dato'}</span>`;

function intervencion(d) {
  const [con, colCon, red] = escenario(d);
  let txt;
  if (d.cs === 0) return '';
  if (d.cs !== 3) txt = 'No se aplica: la intervención solo se aplica en municipios en rojo.';
  else if (!(red > 0)) txt = grupoPct(d) === 0 ? 'No tendría efecto: nadie de la lista pertenece al grupo.' : 'El efecto sería casi nulo.';
  else {
    const final = colCon === 3 ? 'Seguiría en rojo.' : `Pasaría a abstención ${NIVEL[nivelDe(colCon)].toLowerCase()}.`;
    const gente = d.ln != null ? `, unas ${entero(red / 100 * d.ln)} personas más votando` : '';
    txt = `Si ${FRACCION[estado.efecto]} ${esc(GRUPOS[estado.grupo].frase)} que no votan sí votara: <b>${pct(con)}</b>
      (${puntos(red)} menos${gente}). ${final}`;
  }
  return `<section><h3>Con intervención <small>(efecto supuesto)</small></h3><p>${txt}</p></section>`;
}

function razones(d) {
  const rz = d.rz.map(leerRazon);
  if (!rz.length) return '';
  const items = rz.map(r => {
    if (r.valor == null) return `<li>${esc(r.texto)}</li>`;
    const sube = r.valor > 0;
    return `<li class="${sube ? 'sube' : 'baja'}"><span class="flecha" aria-hidden="true">${sube ? '↑' : '↓'}</span>
      <span>${esc(r.texto)} <span class="efecto">(${sube ? 'sube' : 'baja'} ${puntos(Math.abs(r.valor))})</span></span></li>`;
  }).join('');
  return `<section><h3>Por qué</h3><ul class="razones">${items}</ul></section>`;
}

function detalles(d, clave) {
  const avisos = d.av.map(a => BANDERAS[a] || { nombre: a, texto: '' });
  if (d.cs === 3 && d.im[GRUPO_IDX[estado.grupo]]) avisos.push({ nombre: 'Grupo estimado', texto: 'El tamaño del grupo se estimó porque faltaba el dato.' });
  const gpct = grupoPct(d);
  const brecha = d.br == null ? 'Sin dato' : `${puntos(Math.abs(d.br))} ${d.br >= 0 ? 'más' : 'menos'} en intermedias que en presidenciales`;
  return `
    ${avisos.length ? `<p class="cautela">⚠ Dato poco confiable: ${avisos.map(a => esc(a.nombre.toLowerCase())).join(', ')}. Tómalo con cautela.</p>` : ''}
    <details class="detalles"><summary>Más detalles</summary>
      <dl>
        <dt>Lista nominal</dt><dd>${d.ln == null ? '—' : `${entero(d.ln)} personas`}</dd>
        <dt>${esc(GRUPOS[estado.grupo].nombre)}</dt><dd>${gpct == null ? '—' : `${pct(gpct)} de la lista`}</dd>
        <dt>Intermedia vs. presidencial</dt><dd>${brecha}</dd>
        ${avisos.map(a => `<dt>${esc(a.nombre)}</dt><dd>${esc(a.texto)}</dd>`).join('')}
        <dt>Clave INEGI</dt><dd>${esc(clave)}</dd>
      </dl>
    </details>`;
}

function ficha(clave) {
  const d = datos.DATA.municipios[clave];
  const conclusion = d.cs === 0
    ? '<p class="frase">No hay datos de voto de la última elección, por eso no tiene color.</p>'
    : `<p class="frase"><b>${Math.round(d.p)} de cada 100</b> personas de la lista nominal no votarían en 2027 (${pct(d.p)}).</p>${barra(d)}`;
  return `
    <div class="ficha-cabeza">
      <div><h2 id="ficha-titulo" tabindex="-1">${esc(d.n)}</h2><div class="sub">${esc(nombreEstado(d.e))}</div></div>
      <button type="button" class="cerrar" data-accion="cerrar" aria-label="Cerrar ficha" title="Cerrar (Esc)">×</button>
    </div>
    <div class="ficha-cuerpo">
      <section class="conclusion">${insignia(d.cs)}${conclusion}</section>
      ${intervencion(d)}
      ${razones(d)}
      ${detalles(d, clave)}
    </div>`;
}

// ---------- resumen en texto (lector de pantalla) ----------
export function totalNacional() {
  const t = datos.DATA.meta.totales[estado.grupo][estado.efecto];
  return `≈ ${personas(t.personas)} más votarían`;
}

export function resumenTexto() {
  const vista = vistaActiva();
  const n = conteos(vista === 'comparar' ? 'con' : vista);
  const cats = categoriasDe(escala()).filter(c => n[c.cat]);
  const nombre = vista === 'comparar' ? 'Comparación sin y con intervención' : `Mapa ${VISTAS[vista].num}, ${VISTAS[vista].corto}`;
  return `${nombre}: ${cats.map(c => `${entero(n[c.cat])} municipios ${c.nombre.toLowerCase()}`).join(', ')}.`;
}

// ---------- dibujo ----------
let ultima = null;
export function dibujarFicha() {
  const el = $('#ficha');
  if (estado.mun !== ultima) cerrarEtiquetas();
  el.hidden = !estado.mun;
  $('#ficha-contenido').innerHTML = estado.mun ? ficha(estado.mun) : '';
  if (estado.mun && estado.mun !== ultima) {
    el.classList.toggle('expandida', true);
    const d = datos.DATA.municipios[estado.mun];
    $('#anuncio').textContent = `Ficha de ${d.n}, ${nombreEstado(d.e)}`;
  }
  ultima = estado.mun;
  $('#resumen-vista').textContent = resumenTexto();
}

export function enfocarFicha() {
  $('#ficha-titulo')?.focus({ preventScroll: true });
}

export function prepararFicha() {
  const el = $('#ficha');
  el.addEventListener('click', e => {
    if (e.target.closest('[data-accion="cerrar"]')) cambiar({ mun: null });
  });
  // en celular el asa encoge o agranda la hoja
  $('#ficha-asa').addEventListener('click', () => { if (esMovil()) el.classList.toggle('expandida'); });
}
