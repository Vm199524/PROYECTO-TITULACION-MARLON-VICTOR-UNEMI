/**
 * Archivo: api.js
 * Rol: cliente HTTP compartido del frontend.
 * Recibe desde: App.jsx y hooks/servicios que llaman a la API.
 * Se conecta con: appConfig.js para API_BASE y con backend/main.py.
 * Responsabilidades: centralizar axios e inyectar JWT en cada request.
 */

import axios from 'axios';
import { API_BASE } from '../constants/appConfig';

const api = axios.create({
    baseURL: API_BASE
});

// ── INTERCEPTOR DE SEGURIDAD (v2 Gold) ──────────────────────────────────────
// Este bloque intercepta cada petición saliente para inyectar el Token JWT
// si está disponible. Esto permite el aislamiento multiusuario en el servidor.
// Seccion: interceptor que anexa el JWT persistido por App.jsx.
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('quantum_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// ── INTERCEPTOR DE RESPUESTA (sesión revocada) ─────────────────────────────
// Si el backend responde 401/403 en cualquier petición protegida, la sesión
// fue revocada o expiró: se limpia el token y se vuelve al login al instante.
// Se excluye el propio /login para que el error de credenciales se muestre
// en pantalla y no se recargue la página.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error?.response?.status;
        const url = error?.config?.url || '';
        const esLogin = url.includes('/login') || url.includes('/auth');
        if ((status === 401 || status === 403) && !esLogin && typeof window !== 'undefined') {
            // Solo se recarga si REALMENTE habia una sesion que perder. Sin esa
            // condicion, un 401 recibido cuando ya estamos en la pantalla de
            // login volveria a recargar la pagina una y otra vez.
            const habiaSesion = Boolean(localStorage.getItem('quantum_token'));
            localStorage.removeItem('quantum_token');
            if (habiaSesion) {
                // La aplicacion no usa rutas (no hay react-router): la pantalla
                // de login es lo que se muestra cuando no hay token, asi que se
                // vuelve a la raiz en vez de inventar una URL /login.
                window.location.assign('/');
            }
        }
        return Promise.reject(error);
    }
);

export const apiGet = (path, config) => api.get(path, config);
export const apiPost = (path, data, config) => api.post(path, data, config);
export const apiPut = (path, data, config) => api.put(path, data, config);
export const apiDelete = (path, config) => api.delete(path, config);

