import React from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { normalizeQueryResult } from '../utils/queryResult';
import { ChatMessage } from '../components/ChatMessage';


describe('query result contract', () => {
    it('normalizes new contract payload', () => {
        const normalized = normalizeQueryResult({
            status: 'success',
            message: 'Consulta ejecutada',
            data: { columns: ['Total'], rows: [[15]], row_count: 1 },
            render: { type: 'value', title: 'Titulo', subtitle: '' },
            sql: { text: 'SELECT 15', executed: true, corrected: false, dialect: 'sqlserver' },
            analysis: { summary: 'Resumen', steps: ['Paso 1'], confidence: 0.9, source: 'planner' },
        });

        expect(normalized.message).toBe('Consulta ejecutada');
        expect(normalized.render.type).toBe('value');
        expect(normalized.sql.text).toBe('SELECT 15');
        expect(normalized.analysis.steps).toEqual(['Paso 1']);
    });

    it('renders assistant header without legacy identity text', () => {
        // 'content' es el campo que ChatMessage realmente renderiza como texto
        // del asistente (ver App.jsx: setChatHistory pushea { type: 'ai', content, ... }).
        // 'result' solo aporta metadatos estructurados (sql, analysis, etc.).
        const msg = {
            type: 'ai',
            content: 'Soy Asistente IA VicMar Data AI.',
            result: normalizeQueryResult({
                status: 'conversation',
                message: 'Soy Asistente IA VicMar Data AI.',
                data: { columns: [], rows: [], row_count: 0 },
                render: { type: 'text', title: '', subtitle: '' },
                sql: { text: '', executed: false, corrected: false, dialect: 'sqlserver' },
                analysis: { summary: 'Identidad', steps: ['Paso 1'], confidence: 1, source: 'conversation' },
            }),
            activeTab: 'Resultados',
        };

        render(
            <ChatMessage
                msg={msg}
                setChatHistory={() => {}}
                chatHistory={[msg]}
                idx={0}
                deviceType="desktop"
                userAuth={{ role: 'GERENTE_GENERAL', modules: ['RRHH'] }}
                activeModule="RRHH"
            />
        );

        expect(screen.getByText(/Asistente IA VicMar Data AI/i)).toBeInTheDocument();
        expect(screen.queryByText(/Cerebro Analitico/i)).toBeNull();
    });

    it('removes generic row count boilerplate when there are rows', () => {
        const normalized = normalizeQueryResult({
            status: 'success',
            message: 'Se recuperaron 1 registros para su consulta.',
            data: { columns: ['Cantidad'], rows: [[551]], row_count: 1 },
            render: { type: 'table', title: '', subtitle: '' },
            sql: { text: 'SELECT 551 AS Cantidad', executed: true, corrected: false, dialect: 'sqlserver' },
            analysis: { summary: 'Se recuperaron 1 registros para su consulta.', steps: [], confidence: 1, source: 'planner' },
        });

        expect(normalized.message).toBe('');
        expect(normalized.explanation).toBe('');
    });
});
