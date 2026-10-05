/**
 * @file Pruebas de los avisos de error de `LoginView`. Verifican que cada error
 * se muestre una sola vez: un fallo de credenciales va en la franja roja del
 * formulario y sin el botón «Refrescar Sistema» (recargar no corrige una
 * contraseña equivocada y haría parecer que el sistema falló), y un error del
 * sistema (`errorDeSistema`) va solo en el panel azul con ese botón.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
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

        // El mensaje aparece exactamente una vez, en el panel azul con
        // «Refrescar Sistema», y no se repite en la franja roja del formulario.
        expect(screen.getAllByText(ERROR_SISTEMA)).toHaveLength(1);
        expect(screen.getByRole('button', { name: /refrescar sistema/i })).toBeTruthy();
    });

    it('sin error no se muestra ninguno de los dos avisos', () => {
        render(<LoginView {...propsBase()} />);

        expect(screen.queryByText(ERROR_CREDENCIALES)).toBeNull();
        expect(screen.queryByRole('button', { name: /refrescar sistema/i })).toBeNull();
    });
});
