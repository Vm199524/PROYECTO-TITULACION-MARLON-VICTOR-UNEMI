// Service Worker para QuantumBI — Solo activo en producción.
// En desarrollo, Vite sirve módulos con ?v=<hash> dinámico; cachearlos
// provoca "Failed to fetch dynamically imported module" al reiniciar.

const CACHE_NAME = 'quantum-bi-v2';

// Patrones que NUNCA deben cachearse (módulos de Vite dev + HMR)
const NEVER_CACHE = [
    /\?v=/,           // deps de Vite con hash de versión
    /@vite/,          // cliente HMR de Vite
    /@react-refresh/, // React Fast Refresh
    /\.vite\//,       // caché interna de Vite
    /node_modules\//  // módulos pre-bundleados
];

const debeIgnorar = (url) => NEVER_CACHE.some((re) => re.test(url));

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    // Eliminar cachés antiguas al activar la nueva versión
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = event.request.url;

    // Pasar siempre sin tocar: módulos Vite, HMR, peticiones al backend
    if (debeIgnorar(url)) return;

    // Para todo lo demás: network-first, sin caché agresiva
    event.respondWith(fetch(event.request));
});
