// guia de primera visita (3 pasos) y ventana de ayuda
import { almacen, $ } from './util.js';

const CLAVE_GUIA = 'abstencion2027.guiaVista';
const PASOS = [
  { sel: '#buscar', titulo: 'Busca tu municipio', texto: 'Escribe su nombre o el de tu estado. No importan los acentos.' },
  { sel: '#mapas', titulo: 'Haz clic o toca un municipio', texto: 'Su ficha se queda abierta con su riesgo, lo que pasaría con la intervención y el porqué.' },
  { sel: '#pestanas', titulo: 'Elige qué mapa ver', texto: 'Debajo de las pestañas se explica qué muestra cada mapa. «Comparar» pone el antes y el después juntos.' },
];
let paso = 0;
let antes = null;

function colocar() {
  const p = PASOS[paso];
  const objetivo = $(p.sel);
  const r = objetivo.getBoundingClientRect();
  const hueco = $('#guia-hueco');
  const m = 6;
  Object.assign(hueco.style, { left: `${r.left - m}px`, top: `${r.top - m}px`, width: `${r.width + m * 2}px`, height: `${r.height + m * 2}px` });
  $('#guia-titulo').textContent = p.titulo;
  $('#guia-texto').textContent = p.texto;
  $('#guia-paso').textContent = `${paso + 1} de ${PASOS.length}`;
  $('#guia-siguiente').textContent = paso === PASOS.length - 1 ? 'Listo' : 'Siguiente';
  // la tarjeta va debajo del elemento, o encima si no cabe
  const tarjeta = $('#guia-tarjeta');
  const ancho = Math.min(320, window.innerWidth - 32);
  tarjeta.style.width = `${ancho}px`;
  const cabeAbajo = r.bottom + 16 + 170 < window.innerHeight;
  const top = p.sel === '#mapas' ? r.top + r.height / 2 - 80 : cabeAbajo ? r.bottom + 16 : Math.max(16, r.top - 186);
  tarjeta.style.top = `${Math.max(16, top)}px`;
  tarjeta.style.left = `${Math.max(16, Math.min(window.innerWidth - ancho - 16, r.left))}px`;
}

export function abrirGuia() {
  antes = document.activeElement;
  paso = 0;
  $('#guia').hidden = false;
  colocar();
  $('#guia-siguiente').focus();
}

export function cerrarGuia() {
  if ($('#guia').hidden) return false;
  $('#guia').hidden = true;
  almacen.guardar(CLAVE_GUIA, true);
  antes?.focus?.();
  return true;
}

export function prepararGuia() {
  $('#guia-siguiente').addEventListener('click', () => {
    if (paso < PASOS.length - 1) { paso++; colocar(); } else cerrarGuia();
  });
  $('#guia-saltar').addEventListener('click', cerrarGuia);
  $('#guia').addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.stopPropagation(); cerrarGuia(); }
    // el foco se queda dentro de la tarjeta
    if (e.key === 'Tab') {
      const b = [$('#guia-saltar'), $('#guia-siguiente')];
      const i = b.indexOf(document.activeElement);
      e.preventDefault();
      b[(i + (e.shiftKey ? -1 : 1) + b.length) % b.length].focus();
    }
  });
  window.addEventListener('resize', () => { if (!$('#guia').hidden) colocar(); });

  $('#ayuda-ver-guia').addEventListener('click', () => { $('#ayuda').close(); abrirGuia(); });
  $('#ayuda').addEventListener('click', e => { if (e.target.closest('[data-cerrar]')) $('#ayuda').close(); });

}

export function abrirAyuda() {
  const d = $('#ayuda');
  if (!d.open) d.showModal();
}
