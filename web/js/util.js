// utilidades compartidas: formato es-MX, texto seguro y almacenamiento local

export const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const nf1 = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const nf0 = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });

export const pct = v => (v == null ? '—' : nf1.format(v) + '%');
// diferencias entre porcentajes: 1 punto = 1 de cada 100 personas de la lista nominal
export const puntos = (v, dec = 1) => (v == null ? '—'
  : `${v.toLocaleString('es-MX', { minimumFractionDigits: dec, maximumFractionDigits: dec })} ${Math.abs(v) === 1 ? 'punto' : 'puntos'}`);
export const entero = v => (v == null ? '—' : nf0.format(Math.round(v)));
export const decimal = v => (v == null ? '—' : nf1.format(v));

// "1.22 millones de personas" o "18,753 personas"
export const personas = n => (n >= 1e6
  ? `${(n / 1e6).toLocaleString('es-MX', { maximumFractionDigits: 2 })} millones de personas`
  : `${entero(n)} personas`);

// minusculas y sin acentos, para buscar "michoacan" y encontrar "Michoacán"
export const normalizar = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

// localStorage puede fallar (ventana privada, sitio bloqueado): nunca rompe la pagina
export const almacen = {
  leer(clave, defecto) {
    try {
      const v = localStorage.getItem(clave);
      return v == null ? defecto : JSON.parse(v);
    } catch { return defecto; }
  },
  guardar(clave, valor) {
    try { localStorage.setItem(clave, JSON.stringify(valor)); } catch { /* sin almacenamiento */ }
  },
};

export const $ = sel => document.querySelector(sel);
export const $$ = sel => [...document.querySelectorAll(sel)];

export const esMovil = () => window.matchMedia('(max-width: 760px)').matches;

// descarga un Blob con el nombre indicado
export function descargar(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nombre;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// aviso breve en la esquina ("Enlace copiado")
let tAviso;
export function avisar(texto) {
  const el = $('#toast');
  el.textContent = texto;
  el.hidden = false;
  clearTimeout(tAviso);
  tAviso = setTimeout(() => { el.hidden = true; }, 2600);
}
