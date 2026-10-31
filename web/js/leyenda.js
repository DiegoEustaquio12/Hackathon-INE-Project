// leyenda: colores de la vista, apagar/encender categorias, datos poco confiables; se puede plegar siempre
import { datos, estado, cambiar, escala, vistaActiva, categoriasDe, conteos, COLORES, esFragil } from './estado.js';
import { BANDERAS } from './textos.js';
import { esc, entero, almacen, esMovil, $ } from './util.js';

const CLAVE_PLEGADA = 'abstencion2027.leyendaPlegada';
const TITULO = {
  sem: { sin: 'Abstención prevista 2027', con: 'Abstención con intervención', comparar: 'Abstención prevista 2027' },
  dif: 'Cuánto baja la abstención',
  brecha: 'Abstención extra en intermedias',
};

export function dibujarLeyenda() {
  const el = $('#leyenda-cuerpo');
  const esca = escala();
  const vista = vistaActiva();
  const n = conteos(vista);
  const nCon = vista === 'comparar' ? conteos('con') : null;
  const titulo = esca === 'sem' ? TITULO.sem[vista] : TITULO[esca];
  const nFragiles = Object.values(datos.DATA.municipios).filter(esFragil).length;

  const filas = categoriasDe(esca)
    .filter(c => c.cat !== 'nd' || n.nd)
    .map(c => {
      const visible = !estado.ocultas.has(c.cat);
      const cuenta = nCon ? `${entero(n[c.cat] || 0)} → ${entero(nCon[c.cat] || 0)}` : entero(n[c.cat] || 0);
      return `<li><button type="button" class="fila-leyenda" data-cat="${c.cat}" aria-pressed="${visible}"
        title="${visible ? 'Ocultar' : 'Mostrar'} en el mapa">
        <i class="muestra" style="background:${COLORES[c.cat]}"></i>
        <span class="nombre-cat"><b>${esc(c.nombre)}</b>${c.rango ? ` <span class="rango-cat">${esc(c.rango)}</span>` : ''}</span>
        <span class="cuenta" title="municipios">${cuenta}</span></button></li>`;
    }).join('');

  const marcas = [];
  if (vista === 'con' || vista === 'comparar') marcas.push('<li class="marca"><i class="muestra borde"></i>Cambia de color con la intervención</li>');

  el.innerHTML = `
    <div class="leyenda-titulo">
      <b>${esc(titulo)}</b>
      <button type="button" class="cerrar-leyenda" data-accion-leyenda="plegar" aria-label="Ocultar leyenda" title="Ocultar leyenda">×</button>
    </div>
    <ul class="filas">${filas}</ul>
    <p class="leyenda-pie">Clic en un color para ocultarlo. Números: municipios${nCon ? ' (sin → con intervención)' : ''}.</p>
    ${estado.ocultas.size ? '<button type="button" class="enlace mostrar-todos">Mostrar todos</button>' : ''}
    ${marcas.length ? `<ul class="marcas">${marcas.join('')}</ul>` : ''}
    <div class="fragiles">
      <label><input type="checkbox" id="chk-fragiles" ${estado.fragiles ? 'checked' : ''}>
        Marcar datos poco confiables (${entero(nFragiles)})</label>
      <button type="button" class="info" aria-expanded="false" aria-controls="fragiles-ayuda" title="¿Qué significa?">ⓘ</button>
    </div>
    <div id="fragiles-ayuda" class="leyenda-ayuda" hidden>
      Se marcan con contorno punteado:
      <ul>${Object.values(BANDERAS).map(b => `<li><b>${esc(b.nombre)}:</b> ${esc(b.texto)}</li>`).join('')}</ul>
    </div>`;
}

function plegar(si) {
  const el = $('#leyenda');
  el.classList.toggle('plegada', si);
  $('#leyenda-abrir').setAttribute('aria-expanded', String(!si));
  almacen.guardar(CLAVE_PLEGADA, si);
}

export function prepararLeyenda() {
  const el = $('#leyenda');
  // en celular o pantallas bajas empieza plegada, salvo que la persona ya la haya abierto antes
  plegar(almacen.leer(CLAVE_PLEGADA, esMovil() || window.innerHeight < 640));
  $('#leyenda-abrir').addEventListener('click', () => { plegar(false); el.querySelector('.cerrar-leyenda')?.focus(); });

  el.addEventListener('click', e => {
    if (e.target.closest('[data-accion-leyenda="plegar"]')) { plegar(true); $('#leyenda-abrir').focus(); return; }
    const fila = e.target.closest('.fila-leyenda');
    if (fila) {
      const ocultas = new Set(estado.ocultas);
      const cat = fila.dataset.cat;
      ocultas.has(cat) ? ocultas.delete(cat) : ocultas.add(cat);
      cambiar({ ocultas });
      $(`.fila-leyenda[data-cat="${cat}"]`)?.focus();
      return;
    }
    if (e.target.closest('.mostrar-todos')) { cambiar({ ocultas: new Set() }); return; }
    const info = e.target.closest('.info');
    if (info) {
      const ayuda = document.getElementById(info.getAttribute('aria-controls'));
      ayuda.hidden = !ayuda.hidden;
      info.setAttribute('aria-expanded', String(!ayuda.hidden));
    }
  });
  el.addEventListener('change', e => {
    if (e.target.id === 'chk-fragiles') {
      cambiar({ fragiles: e.target.checked });
      $('#chk-fragiles')?.focus();
    }
  });
}
