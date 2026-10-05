/**
 * @file Cliente HTTP compartido del frontend. Centraliza la instancia de axios
 * con `API_BASE` (appConfig.js), adjunta el JWT guardado por App.jsx en cada
 * petición al backend FastAPI y devuelve al login cuando la sesión se revoca.
 * Lo usan App.jsx, los hooks y los componentes que llaman a la API.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import axios from 'axios';
import { API_BASE } from '../constants/appConfig';

const api = axios.create({
    baseURL: API_BASE
});

// Interceptor de petición: agrega el JWT guardado por App.jsx en
// `quantum_token`, si existe, para que el servidor aísle los datos de cada
// usuario.
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('quantum_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

// Interceptor de respuesta (sesión revocada): si el backend responde 401/403 en cualquier petición protegida, la sesión
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
            // Solo se recarga si había una sesión que perder; si no, un 401
            // recibido en la pantalla de login recargaría la página en bucle.
            const habiaSesion = Boolean(localStorage.getItem('quantum_token'));
            localStorage.removeItem('quantum_token');
            if (habiaSesion) {
                // La aplicación no usa rutas (no hay react-router): el login se
                // muestra cuando no hay token, así que se vuelve a la raíz.
                window.location.assign('/');
            }
        }
        return Promise.reject(error);
    }
);

/**
 * Envía una petición GET autenticada.
 * @param {string} path Ruta relativa a `API_BASE` (p. ej. '/context-overview').
 * @param {import('axios').AxiosRequestConfig} [config] Opciones de axios.
 * @returns {Promise<import('axios').AxiosResponse>} Respuesta del backend.
 */
export const apiGet = (path, config) => api.get(path, config);
/**
 * Envía una petición POST autenticada.
 * @param {string} path Ruta relativa a `API_BASE`.
 * @param {*} [data] Cuerpo de la petición.
 * @param {import('axios').AxiosRequestConfig} [config] Opciones de axios.
 * @returns {Promise<import('axios').AxiosResponse>} Respuesta del backend.
 */
export const apiPost = (path, data, config) => api.post(path, data, config);
/**
 * Envía una petición PUT autenticada.
 * @param {string} path Ruta relativa a `API_BASE`.
 * @param {*} [data] Cuerpo de la petición.
 * @param {import('axios').AxiosRequestConfig} [config] Opciones de axios.
 * @returns {Promise<import('axios').AxiosResponse>} Respuesta del backend.
 */
export const apiPut = (path, data, config) => api.put(path, data, config);
/**
 * Envía una petición DELETE autenticada.
 * @param {string} path Ruta relativa a `API_BASE`.
 * @param {import('axios').AxiosRequestConfig} [config] Opciones de axios.
 * @returns {Promise<import('axios').AxiosResponse>} Respuesta del backend.
 */
export const apiDelete = (path, config) => api.delete(path, config);

