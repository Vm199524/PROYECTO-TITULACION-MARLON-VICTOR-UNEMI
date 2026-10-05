/**
 * @file Límite de errores de React. Envuelve la aplicación en App.jsx para que un
 * fallo de renderizado en un componente hijo (por ejemplo, un gráfico) no deje la
 * pantalla en blanco: atrapa el error y muestra el mensaje con su traza.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */

import React from 'react';

/**
 * Captura los errores de renderizado de sus hijos y muestra una pantalla de
 * respaldo con el mensaje y la traza en lugar de desmontar toda la interfaz.
 *
 * @param {object} props
 * @param {React.ReactNode} props.children - Árbol de componentes que protege.
 * @returns {JSX.Element} Los hijos, o la pantalla de error si alguno falló.
 */
export class ErrorBoundary extends React.Component {
    constructor(props) { super(props); this.state = { hasError: false, error: null }; }
    static getDerivedStateFromError(error) { return { hasError: true, error }; }
    render() {
        if (this.state.hasError) {
            return (
                <div style={{ background: '#020617', color: '#f87171', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace', padding: '40px' }}>
                    <h1 style={{ fontSize: '24px', marginBottom: '16px' }}>? Error de Renderizado</h1>
                    <pre style={{ background: '#0f172a', padding: '20px', borderRadius: '12px', maxWidth: '800px', overflow: 'auto', fontSize: '13px', color: '#fca5a5' }}>
                        {this.state.error?.toString()}{'\n'}{this.state.error?.stack}
                    </pre>
                </div>
            );
        }
        return this.props.children;
    }
}

