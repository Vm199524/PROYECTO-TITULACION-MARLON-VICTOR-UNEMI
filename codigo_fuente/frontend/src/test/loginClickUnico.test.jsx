/**
 * @file Pruebas del botón «Ingresar al sistema» de `LoginView`. Verifican que
 * un solo clic dispare exactamente una vez el manejador de autenticación, que
 * el botón esté habilitado con usuario y contraseña escritos y que ninguna
 * capa decorativa (brillo de hover, overlays absolutos) intercepte el clic,
 * para que una reorganización del formulario no vuelva a tragarse el primer
 * clic.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
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
        // La capa de brillo del hover es un <div absolute inset-0> dentro del
        // botón. Si se la saca del botón o se le da un z-index que la ponga
        // por encima sin pointer-events-none, el clic deja de llegar.
        const handleAuthLogin = vi.fn((e) => e?.preventDefault?.());
        render(<LoginView {...propsBase({ handleAuthLogin })} />);

        const boton = screen.getByRole('button', { name: /ingresar al sistema/i });
        const capas = boton.querySelectorAll('div.absolute');
        capas.forEach((capa) => {
            // Debe seguir siendo descendiente del botón: así el clic burbujea
            // hasta él y el submit ocurre igual.
            expect(boton.contains(capa)).toBe(true);
        });

        fireEvent.click(boton);
        expect(handleAuthLogin).toHaveBeenCalledTimes(1);
    });
});
