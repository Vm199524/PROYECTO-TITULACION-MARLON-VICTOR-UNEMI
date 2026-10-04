/**
 * ============================================================================
 * FICHA TÉCNICA DEL COMPONENTE [FRONTEND-UI-CORE-01]
 * ============================================================================
 * ARCHIVO: NewQueryButton.jsx
 * MÓDULO: UI / Action Buttons
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Es el botón de "Pizarrón Limpio". Permite al usuario abandonar 
 * rápidamente una conversación en curso y empezar una nueva consulta 
 * desde cero sin perder el historial anterior.
 * 
 * 📍 PUNTO DE INTERFAZ:
 * Área de acciones destacadas en el menú lateral principal.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Purga del historial activo en memoria caché (`chatHistory`).
 * - Genera una nueva ID de sesión aleatoria de forma implícita.
 * - Componente visualmente prominente para guiar la interacción fluida.
 * ============================================================================
 */


import React from 'react';
import { Plus } from 'lucide-react';

export function NewQueryButton({ startNewChat }) {
    return (
        <div className="px-2">
            <button onClick={startNewChat}
                className="w-full flex items-center justify-start gap-4 py-5 px-6 rounded-[24px] border border-violet-500/40 text-violet-300 font-black uppercase tracking-[0.3em] text-[12px] hover:bg-violet-500/15 hover:text-white transition-all duration-500 group">
                <Plus size={20} className="group-hover:rotate-90 transition-transform duration-500" />
                Nueva Consulta
            </button>
        </div>
    );
}



