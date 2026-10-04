/**
 * Archivo: loginClickUnico.test.jsx
 * Rol: proteger el comportamiento "un solo clic entra al sistema".
 *
 * Defecto detectado en pruebas (30/08/2026): "hay que dar click como 3 veces
 * al boton de ingresar para poder ingresar al sistema, y ya estaba arreglado
 * que con un solo click de una ingresaba". Esta prueba deja fijado que UN
 * clic sobre "Ingresar al sistema" dispara exactamente UNA vez el handler de
 * autenticacion, para que ninguna reorganizacion del formulario (paddings,
 * capas de hover, overlays absolutos) vuelva a tragarse el primer clic sin
 * que nadie lo note.
 */
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent, screen } from '@testing-library/react';

import { LoginView } from '../pages/Login';

const propsBase = (overrides = {}) => ({
    isConnected: false,
    loading: false,
    authPending: false,
    isVerifying: true,
    isRestoringSession: false,
    showAdvanced: false,
    showDevOptions: false,
    error: null,
    tempCreds: { username: 'adminvm', password: 'secreta123' },
    setTempCreds: () => {},
    showPassword: false,
    setShowPassword: () => {},
    handleAuthLogin: () => {},
    handleConnect: () => {},
    cancelSessionRestore: () => {},
    setIsVerifying: () => {},
    setError: () => {},
    setShowAdvanced: () => {},
    handleTitleClick: () => {},
    maskedHost: '***',
    showHost: false,
    setShowHost: () => {},
    connInfo: { database: '', host: '', auth_type: '' },
    setConnInfo: () => {},
    ...overrides,
});

describe('Login — un solo clic para ingresar', () => {
    it('un clic en "Ingresar al sistema" dispara el login exactamente una vez', () => {
        const handleAuthLogin = vi.fn((e) => e?.preventDefault?.());
        render(<LoginView {...propsBase({ handleAuthLogin })} />);

        const boton = screen.getByRole('button', { name: /ingresar al sistema/i });
        fireEvent.click(boton);

        expect(handleAuthLogin).toHaveBeenCalledTimes(1);
    });

    it('el boton esta habilitado cuando ya hay usuario y contrasena escritos', () => {
        render(<LoginView {...propsBase()} />);
        const boton = screen.getByRole('button', { name: /ingresar al sistema/i });
        expect(boton).not.toBeDisabled();
    });

    it('ninguna capa decorativa del boton intercepta el clic (pointer-events)', () => {
        // La capa de brillo del hover es un <div absolute inset-0> DENTRO del
        // boton. Si algun dia se la saca del boton o se le da un z-index que la
        // ponga por encima sin pointer-events-none, el clic dejaria de llegar.
        const handleAuthLogin = vi.fn((e) => e?.preventDefault?.());
        render(<LoginView {...propsBase({ handleAuthLogin })} />);

        const boton = screen.getByRole('button', { name: /ingresar al sistema/i });
        const capas = boton.querySelectorAll('div.absolute');
        capas.forEach((capa) => {
            // Debe seguir siendo descendiente del boton: asi el clic burbujea
            // hasta el y el submit ocurre igual.
            expect(boton.contains(capa)).toBe(true);
        });

        fireEvent.click(boton);
        expect(handleAuthLogin).toHaveBeenCalledTimes(1);
    });
});
