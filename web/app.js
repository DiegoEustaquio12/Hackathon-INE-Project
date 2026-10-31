// punto de entrada: carga los datos, arma la pagina y vuelve a dibujar todo con cada cambio de estado
import { datos, estado, cambiar, alCambiar, leerURL, escribirURL, recalcular } from './js/estado.js';
import { VISTAS, QUE_COMPARAR } from './js/textos.js';
import { esc, esMovil, almacen, $, $$ } from './js/util.js';
import { mapas, crearMapa, refrescarMapas, aplicarComparacion, prepararCortina, verTodo, zoomMunicipio, cerrarEtiquetas } from './js/mapa.js';
import { dibujarLeyenda, prepararLeyenda } from './js/leyenda.js';
import { dibujarFicha, prepararFicha, totalNacional } from './js/ficha.js';
import { prepararBuscador, recordar } from './js/buscador.js';
import { dibujarLista, prepararLista } from './js/lista.js';
import { ACCIONES } from './js/exportar.js';
import { prepararGuia, abrirAyuda, cerrarGuia } from './js/guia.js';

const CLAVE_PISTA = 'abstencion2027.pistaVista';
const pestanaActiva = () => (estado.comparar ? 'comparar' : estado.vista);

// ---------- dibujo de controles ----------
function dibujarControles() {
  const activa = pestanaActiva();
  for (const b of $$('[data-tab]')) b.setAttribute('aria-pressed', String(b.dataset.tab === activa));
  const mas = $('#boton-mas-mapas');
  const enMas = activa === 'dif' || activa === 'brecha';
  mas.classList.toggle('activo', enMas);
  mas.textContent = enMas ? `${VISTAS[activa].corto} ▾` : 'Más mapas ▾';

  // linea "Que muestra": que representa el mapa activo
  $('#que-nombre').textContent = activa === 'comparar' ? 'Comparar ·' : `Mapa ${VISTAS[activa].num} ·`;
  $('#que-texto').textContent = activa === 'comparar' ? QUE_COMPARAR[estado.comparar] : VISTAS[activa].que;
  // los controles de la intervencion solo aparecen donde cambian el mapa
  $('#intervencion').hidden = !['con', 'dif', 'comparar'].includes(activa);
  $('#sel-grupo').value = estado.grupo;
  $('#sel-efecto').value = estado.efecto;
  $('#total').textContent = totalNacional();
  $('#modo-comparar').hidden = activa !== 'comparar';
  for (const b of $$('[data-comparar]')) b.setAttribute('aria-pressed', String(b.dataset.comparar === estado.comparar));

  const enLista = estado.panel === 'lista';
  $('#boton-lista').textContent = enLista ? 'Mapa' : 'Lista';
  $('#boton-lista').setAttribute('aria-pressed', String(enLista));
  $('#area-mapa').hidden = enLista;
  $('#lista').hidden = !enLista;
  $('#pista').hidden = !!estado.mun || almacen.leer(CLAVE_PISTA, false);

  document.body.classList.toggle('presentacion', estado.presentar);
  document.documentElement.classList.toggle('presentando', estado.presentar);
}

function render(parcial = {}) {
  if ('comparar' in parcial) aplicarComparacion();
  if ('vista' in parcial || 'comparar' in parcial) cerrarEtiquetas();
  dibujarControles();
  refrescarMapas();
  dibujarLeyenda();
  dibujarFicha();
  dibujarLista();
  if (parcial.mun) {
    recordar(parcial.mun);
    almacen.guardar(CLAVE_PISTA, true);
  }
  if ('panel' in parcial) {
    if (estado.panel === 'mapa') for (const o of Object.values(mapas)) o.map.invalidateSize({ animate: false });
    // al volver a la lista, la fila del municipio elegido queda a la vista
    else $('#tabla tr.sel')?.scrollIntoView({ block: 'center' });
  }
  if ('presentar' in parcial) setTimeout(() => {
    for (const o of Object.values(mapas)) o.map.invalidateSize({ animate: false });
    if (estado.mun) zoomMunicipio(estado.mun); else verTodo();
  }, 250);
}

// ---------- acciones ----------
// en celular solo hay cortina: dos mapas apilados quedan demasiado chicos
const modoComparar = modo => (esMovil() ? 'cortina' : modo || 'cortina');

function irA(tab) {
  if (tab === 'comparar') {
    cambiar({ comparar: modoComparar(estado.comparar), panel: 'mapa' });
    setTimeout(() => (estado.mun ? zoomMunicipio(estado.mun) : verTodo()), 60);
  } else {
    const salia = !!estado.comparar;
    cambiar({ vista: tab, comparar: '', orden: '' });
    if (salia) setTimeout(() => (estado.mun ? zoomMunicipio(estado.mun) : verTodo()), 60);
  }
}

function alternarPresentacion() {
  const entrar = !estado.presentar;
  // el diseño grande se aplica siempre; la pantalla completa solo donde el navegador la permite (no en iPhone)
  cambiar({ presentar: entrar, panel: 'mapa' });
  const pedir = entrar
    ? document.documentElement.requestFullscreen?.()
    : document.fullscreenElement && document.exitFullscreen();
  Promise.resolve(pedir).catch(() => {});
}

const ACCION = {
  ...ACCIONES,
  ayuda: abrirAyuda,
  presentar: alternarPresentacion,
  'alternar-panel': () => cambiar({ panel: estado.panel === 'lista' ? 'mapa' : 'lista' }),
};

// menus desplegables (Mas mapas, ⋯)
function cerrarMenus(excepto) {
  for (const b of $$('[aria-haspopup="true"]')) {
    if (b === excepto) continue;
    b.setAttribute('aria-expanded', 'false');
    document.getElementById(b.getAttribute('aria-controls')).hidden = true;
  }
}

function prepararControles() {
  for (const b of $$('[data-tab]')) b.addEventListener('click', () => { cerrarMenus(); irA(b.dataset.tab); });
  for (const b of $$('[data-comparar]')) b.addEventListener('click', () => cambiar({ comparar: modoComparar(b.dataset.comparar) }));
  $('#sel-grupo').addEventListener('change', e => cambiar({ grupo: e.target.value }));
  $('#sel-efecto').addEventListener('change', e => cambiar({ efecto: e.target.value }));

  document.addEventListener('click', e => {
    const menu = e.target.closest('[aria-haspopup="true"]');
    if (menu) {
      const abrir = menu.getAttribute('aria-expanded') !== 'true';
      cerrarMenus(menu);
      menu.setAttribute('aria-expanded', String(abrir));
      const lista = document.getElementById(menu.getAttribute('aria-controls'));
      lista.hidden = !abrir;
      if (abrir) lista.querySelector('button')?.focus();
      return;
    }
    const acc = e.target.closest('[data-accion]');
    if (acc && ACCION[acc.dataset.accion] && !acc.closest('#ficha')) {
      cerrarMenus();
      ACCION[acc.dataset.accion]();
      return;
    }
    if (!e.target.closest('.menu-lista')) cerrarMenus();
  });

  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement && estado.presentar) cambiar({ presentar: false });
  });
  window.addEventListener('beforeprint', () => { for (const o of Object.values(mapas)) o.map.invalidateSize({ animate: false }); });
  // si la ventana se angosta mientras se compara lado a lado, pasa a cortina
  window.matchMedia('(max-width: 760px)').addEventListener('change', e => {
    if (e.matches && estado.comparar === 'lado') cambiar({ comparar: 'cortina' });
  });
}

// ---------- atajos de teclado ----------
function prepararAtajos() {
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      cerrarEtiquetas();
      const abierto = $$('[aria-haspopup="true"]').find(b => b.getAttribute('aria-expanded') === 'true');
      if (abierto) { cerrarMenus(); abierto.focus(); return; }
      if (cerrarGuia()) return;
      if ($('#ayuda').open) return; // el <dialog> se cierra solo
      if (estado.mun) { cambiar({ mun: null }); return; }
      if (estado.presentar) alternarPresentacion();
      return;
    }
    const escribiendo = e.target.closest('input, select, textarea, [contenteditable]');
    if (escribiendo || e.ctrlKey || e.metaKey || e.altKey || $('#ayuda').open || !$('#guia').hidden) return;
    const tabs = { 1: 'sin', 2: 'con', 3: 'dif', 4: 'brecha' };
    const k = e.key.toLowerCase();
    if (k === '/') { e.preventDefault(); $('#buscar').focus(); }
    else if (tabs[k]) irA(tabs[k]);
    else if (k === 'c') irA(estado.comparar ? estado.vista : 'comparar');
    else if (k === 'l') ACCION['alternar-panel']();
    else if (k === 'p') alternarPresentacion();
    else if (e.key === '?') { e.preventDefault(); abrirAyuda(); }
  });
}

// ---------- arranque ----------
const leer = r => {
  if (!r.ok) throw new Error(`${r.url} → ${r.status}`);
  return r.json();
};

function cargar() {
  const cargando = $('#cargando');
  cargando.innerHTML = '<div class="esqueleto" aria-hidden="true"></div><p>Cargando municipios…</p>';
  Promise.all([
    fetch('municipios_web.geojson').then(leer),
    fetch('escenarios.json').then(leer),
    fetch('estados_web.geojson').then(leer).catch(() => null), // los limites estatales son opcionales
  ]).then(([geo, data, edos]) => {
    datos.GEO = geo;
    datos.DATA = data;
    datos.ESTADOS = edos;
    leerURL();
    if (estado.comparar) estado.comparar = modoComparar(estado.comparar);
    if (estado.panel === 'lista' && esMovil()) estado.panel = 'mapa';
    recalcular();

    crearMapa('mapaA', 'A');
    prepararControles();
    prepararCortina();
    prepararLeyenda();
    prepararFicha();
    prepararBuscador();
    prepararLista();
    prepararAtajos();
    prepararGuia();
    alCambiar(render);
    cargando.remove();
    render({ comparar: estado.comparar });
    escribirURL();
    // al abrir ya comparando, los mapas son mas angostos: se vuelve a encuadrar
    if (estado.mun) setTimeout(() => zoomMunicipio(estado.mun), 100);
    else if (estado.comparar) setTimeout(verTodo, 150);
  }).catch(err => {
    cargando.innerHTML = `<div class="error-carga"><p><b>No se pudo cargar el mapa.</b></p>
      <p>Revisa tu conexión e inténtalo de nuevo. Si abriste el archivo con doble clic, ábrelo con un servidor local
      (<code>python3 -m http.server</code> dentro de la carpeta <code>web</code>).</p>
      <button type="button" class="boton primario" id="reintentar">Reintentar</button>
      <p class="nota">${esc(err)}</p></div>`;
    $('#reintentar').addEventListener('click', cargar);
  });
}

cargar();
