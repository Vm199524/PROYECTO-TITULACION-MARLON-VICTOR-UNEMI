/**
 * @file Pruebas de la identidad que muestra `DesktopHeader`. Verifican que,
 * mientras `userAuth` sea null y no se sepa quién es el usuario, la cabecera
 * no escriba ningún nombre ni rol de relleno (muestra el esqueleto «Cargando
 * perfil»), y que, cuando el dato llega, muestre el nombre y el rol reales,
 * para que un administrador nunca vea un perfil ajeno como «Analista».
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { DesktopHeader } from '../components/DesktopHeader';

// La cabecera pide el avatar a /profile al montarse. En la prueba no hay
// backend ni token: la API se simula para que no salga ninguna petición real.
vi.mock('../services/api', () => ({
    apiGet: () => Promise.resolve({ data: { profile: { avatar: null } } }),
    apiPost: () => Promise.resolve({ data: {} }),
}));

const propsBase = {
    connInfo: { database: 'MONT', selected_company_code: 'MONT' },
    handleLogout: () => { },
    openQuantumCore: () => { },
    availableDBs: [],
    fetchingDBs: false,
    loadDatabases: () => { },
    handleConnect: () => Promise.resolve(),
};

describe('DesktopHeader — identidad del usuario', () => {
    it('sin userAuth todavía, no escribe ningún perfil inventado', () => {
        render(<DesktopHeader {...propsBase} userAuth={null} />);
        expect(screen.queryByText('Analista')).toBeNull();
        expect(screen.queryByText('Administrador')).toBeNull();
        // En su lugar queda el esqueleto, que sí anuncia lo que está pasando.
        expect(screen.getByLabelText('Cargando perfil')).toBeTruthy();
    });

    it('con la sesión ya verificada, muestra el nombre y el rol reales', () => {
        render(
            <DesktopHeader
                {...propsBase}
                userAuth={{ name: 'Desarrollador', role: 'ADMINISTRADOR' }}
            />
        );
        expect(screen.getByText('Desarrollador')).toBeTruthy();
        expect(screen.getByText('Administrador')).toBeTruthy();
        expect(screen.queryByText('Analista')).toBeNull();
        expect(screen.queryByLabelText('Cargando perfil')).toBeNull();
    });

    it('un rol que no es administrador no se muestra como Administrador', () => {
        render(
            <DesktopHeader
                {...propsBase}
                userAuth={{ name: 'Carlos Espinoza', role: 'CONTABILIDAD' }}
            />
        );
        expect(screen.getByText('Contabilidad')).toBeTruthy();
        expect(screen.queryByText('Administrador')).toBeNull();
    });
});
