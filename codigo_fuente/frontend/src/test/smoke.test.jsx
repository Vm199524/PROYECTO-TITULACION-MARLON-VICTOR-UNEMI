import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent, screen } from '@testing-library/react';

import { SessionHistory } from '../components/SessionHistory';
import { NewQueryButton } from '../components/NewQueryButton';
import { ContextNodes } from '../components/ContextNodes';
import { SidebarFooter } from '../components/SidebarFooter';
import { ChatArea } from '../components/ChatArea';
import { DataChannels } from '../components/views/DataChannels';
import { AnalysisAreas } from '../components/views/AnalysisAreas';
import { DashboardMobile } from '../mobile/DashboardMobile';

vi.mock('../hooks/useContextOverview', () => ({
    useContextOverview: () => ({
        overview: {
            profile: { business_name: 'AGRINAG', modules: ['RRHH'] },
            summary: 'Resumen adaptativo de prueba.',
            kpis: [
                { id: 'active_people', label: 'Trabajadores Activos', display_value: '342', icon: 'users', hint: 'Test' },
            ],
            areas: [
                { id: 'rrhh', name: 'Capital Humano', desc: 'Area lista', status: 'ready' },
            ],
            quick_questions: ['Cuantos trabajadores activos hay?'],
        },
        loading: false,
        error: '',
        reloadOverview: () => Promise.resolve(null),
    }),
}));

describe('UI smoke tests', () => {
    it('renders SessionHistory', () => {
        render(
            <SessionHistory
                sortedSessions={[{ id: 1, name: 'Test', timestamp: '10:00', pinned: false }]}
                activeSessionId={1}
                editingId={null}
                tempSessionName=""
                menuOpenId={null}
                loadSession={() => { }}
                setMenuOpenId={() => { }}
                togglePinSession={() => { }}
                renameSession={() => { }}
                saveNewName={() => { }}
                setTempSessionName={() => { }}
                deleteSession={() => { }}
            />
        );
        expect(true).toBe(true);
    });

    it('renders NewQueryButton', () => {
        render(<NewQueryButton startNewChat={() => { }} />);
        expect(true).toBe(true);
    });

    it('renders ContextNodes', () => {
        render(<ContextNodes />);
        expect(true).toBe(true);
    });

    it('renders SidebarFooter', () => {
        render(<SidebarFooter maskedHost="****" showHost={false} setShowHost={() => { }} />);
        expect(true).toBe(true);
    });

    it('renders ChatArea', () => {
        render(
            <ChatArea
                chatHistory={[]}
                setChatHistory={() => { }}
                deviceType="desktop"
                userAuth={{}}
                loading={false}
                prompt=""
                setPrompt={() => { }}
                handleQuery={() => { }}
                correctionHint={null}
                correct={(text) => ({ text, wasCorrected: false })}
                setCorrectionHint={() => { }}
                activeModule={null}
                textareaRef={{ current: null }}
                chatEndRef={{ current: null }}
            />
        );
        expect(true).toBe(true);
    });

    it('renders DataChannels', () => {
        render(
            <DataChannels
                availableDBs={['CHAT', 'RRHH']}
                connInfo={{
                    host: 'MANUKO',
                    database: 'RRHH',
                    auth_type: 'Windows Authentication',
                    driver: 'ODBC Driver 17 for SQL Server',
                    user: '',
                    password: '',
                }}
                setConnInfo={() => { }}
                loadDatabases={() => { }}
                handleConnect={() => Promise.resolve()}
            />
        );
        expect(true).toBe(true);
    });

    it('renders AnalysisAreas', () => {
        render(<AnalysisAreas dbId="RRHH" />);
        expect(true).toBe(true);
    });

    // Rediseño móvil (29/08/2026): DashboardMobile ahora monta las mismas
    // vistas pesadas que escritorio (BentoDashboard, DataChannels,
    // AdminUsuarios, AdminAuditoria) detrás de una barra de navegación
    // nueva — este smoke test es la única prueba automatizada de que ese
    // cableado no revienta al montar, dado que no hay forma de correr un
    // navegador real en este entorno para verlo con los ojos.
    const propsBaseDashboardMobile = {
        isSidebarOpen: false, setIsSidebarOpen: () => {},
        chatHistory: [], setChatHistory: () => {},
        deviceType: 'mobile', userAuth: { name: 'Admin', role: 'ADMINISTRADOR' },
        activeModule: null, setActiveModule: () => {},
        connInfo: { database: 'MONT', selected_company_code: 'MONT' }, setConnInfo: () => {},
        availableDBs: [], fetchingDBs: false, loadDatabases: () => {}, handleConnect: () => Promise.resolve(),
        loading: false, prompt: '', setPrompt: () => {}, handleQuery: () => {}, cancelQuery: () => {},
        correctionHint: null, correct: (t) => ({ text: t, wasCorrected: false }), setCorrectionHint: () => {},
        textareaRef: { current: null }, chatEndRef: { current: null },
        activeCapabilities: [], activeSessionId: null, sortedSessions: [],
        menuOpenId: null, setMenuOpenId: () => {}, editingId: null, setEditingId: () => {},
        tempSessionName: '', setTempSessionName: () => {},
        startNewChat: () => {}, loadSession: () => {}, togglePinSession: () => {},
        renameSession: () => {}, saveNewName: () => {}, deleteSession: () => {},
        showHost: false, setShowHost: () => {}, maskedHost: '',
        handleLogout: () => {}, biPulse: null,
    };

    it('renders DashboardMobile (pestaña Chat, por defecto)', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} />);
        expect(true).toBe(true);
    });

    it('DashboardMobile: cambiar a la pestaña Indicadores no revienta', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} />);
        fireEvent.click(screen.getByText('Indicadores'));
        expect(true).toBe(true);
    });

    it('DashboardMobile: cambiar a la pestaña Datos no revienta', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} />);
        fireEvent.click(screen.getByText('Datos'));
        expect(true).toBe(true);
    });

    it('DashboardMobile: abrir "Más" muestra, siendo ADMINISTRADOR, el grupo Administración', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} isSidebarOpen />);
        expect(screen.getByText('Usuarios')).toBeTruthy();
        expect(screen.getByText('Nuevo Usuario')).toBeTruthy();
        expect(screen.getByText('Auditoría')).toBeTruthy();
    });

    it('DashboardMobile: un rol sin permisos de administrador no ve el grupo Administración', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} isSidebarOpen userAuth={{ name: 'Contador', role: 'CONTABILIDAD' }} />);
        expect(screen.queryByText('Usuarios')).toBeNull();
        expect(screen.queryByText('Auditoría')).toBeNull();
    });

    it('DashboardMobile: navegar a Usuarios desde "Más" no revienta (rol ADMINISTRADOR)', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} isSidebarOpen />);
        fireEvent.click(screen.getByText('Usuarios'));
        expect(true).toBe(true);
    });

    it('DashboardMobile: navegar a Auditoría desde "Más" no revienta (rol ADMINISTRADOR)', () => {
        render(<DashboardMobile {...propsBaseDashboardMobile} isSidebarOpen />);
        fireEvent.click(screen.getByText('Auditoría'));
        expect(true).toBe(true);
    });

});
