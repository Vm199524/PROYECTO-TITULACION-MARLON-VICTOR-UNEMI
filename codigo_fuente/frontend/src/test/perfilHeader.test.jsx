/**
 * perfilHeader.test.jsx — El header nunca inventa una identidad.
 *
 * Contexto del bug (31/08/2026). Con el "login instantáneo" (App.jsx >
 * handleAuthLogin) el shell se pinta ANTES de que /login responda, así que
 * `userAuth` es null durante esos segundos. DesktopHeader rellenaba ese hueco
 * con `userAuth?.name || 'Analista'`: el usuario entraba con su cuenta de
 * ADMINISTRADOR y leía "Analista" en su propio header. Si además /login
 * fallaba (por ejemplo, porque el almacén de usuarios en GCS no respondía),
 * ese perfil ajeno era lo único que llegaba a ver.
 *
 * Estas pruebas fijan la regla: mientras no se sepa quién es el usuario, el
 * header no escribe ningún nombre ni ningún rol; cuando el dato llega, muestra
 * el real. Sirven de red para que el fallback inventado no vuelva a colarse.
 */
import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { DesktopHeader } from '../components/DesktopHeader';

// El header pide el avatar a /profile al montar. En un test no hay backend ni
// token: se corta aquí para que no salga ninguna petición real.
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
