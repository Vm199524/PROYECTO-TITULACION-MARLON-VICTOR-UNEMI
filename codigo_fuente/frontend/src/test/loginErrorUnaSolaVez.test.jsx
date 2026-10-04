/**
 * loginErrorUnaSolaVez.test.jsx — el error de credenciales se dice UNA vez.
 *
 * Defecto detectado en pruebas (31/08/2026): al escribir mal la
 * contraseña, "Fallo de Autoridad: Verifique Identificador y Código" aparecía
 * dos veces en la misma pantalla — en la franja roja del formulario, que es la
 * que corresponde, y otra vez debajo del botón en un panel azul con un botón
 * "Refrescar Sistema". Ese panel es para cuando el sistema no responde:
 * recargar la página no arregla una contraseña equivocada, así que ofrecerlo
 * ahí solo confunde y hace parecer que el sistema falló.
 *
 * La regla que fijan estas pruebas: el panel de "refrescar" se muestra solo
 * cuando el error es del sistema (`errorDeSistema`), nunca para un fallo de
 * credenciales.
 */
import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { LoginView } from '../pages/Login';

const ERROR_CREDENCIALES = 'Fallo de Autoridad: Verifique Identificador y Código.';
const ERROR_SISTEMA = 'TIEMPO DE ESPERA AGOTADO: El servidor SQL es demasiado lento o el Host no responde.';

const propsBase = (overrides = {}) => ({
    isConnected: false,
    loading: false,
    authPending: false,
    isVerifying: true,
    isRestoringSession: false,
    showAdvanced: false,
    showDevOptions: false,
    error: null,
    errorDeSistema: false,
    tempCreds: { username: 'admin', password: 'equivocada' },
    setTempCreds: () => { },
    showPassword: false,
    setShowPassword: () => { },
    handleAuthLogin: () => { },
    handleConnect: () => { },
    cancelSessionRestore: () => { },
    setIsVerifying: () => { },
    setError: () => { },
    setShowAdvanced: () => { },
    handleTitleClick: () => { },
    maskedHost: '***',
    showHost: false,
    setShowHost: () => { },
    connInfo: { database: '', host: '', auth_type: '' },
    setConnInfo: () => { },
    ...overrides,
});

describe('Login — el error no se duplica', () => {
    it('un fallo de credenciales se muestra una sola vez y sin "Refrescar Sistema"', () => {
        render(<LoginView {...propsBase({ error: ERROR_CREDENCIALES, errorDeSistema: false })} />);

        expect(screen.getAllByText(ERROR_CREDENCIALES)).toHaveLength(1);
        expect(screen.queryByRole('button', { name: /refrescar sistema/i })).toBeNull();
    });

    it('un fallo del sistema se muestra una sola vez, en el panel azul', () => {
        render(<LoginView {...propsBase({ error: ERROR_SISTEMA, errorDeSistema: true })} />);

        // El mensaje aparece EXACTAMENTE una vez — en el panel azul con
        // "Refrescar Sistema" — y no se repite en la franja roja del
        // formulario (bug reportado 31/08/2026: salía 2 veces repetido).
        expect(screen.getAllByText(ERROR_SISTEMA)).toHaveLength(1);
        expect(screen.getByRole('button', { name: /refrescar sistema/i })).toBeTruthy();
    });

    it('sin error no se muestra ninguno de los dos avisos', () => {
        render(<LoginView {...propsBase()} />);

        expect(screen.queryByText(ERROR_CREDENCIALES)).toBeNull();
        expect(screen.queryByRole('button', { name: /refrescar sistema/i })).toBeNull();
    });
});
