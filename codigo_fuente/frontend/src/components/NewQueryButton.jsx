/**
 * @file Botón «Nueva Consulta». Permite cerrar la conversación en curso y empezar
 * una consulta desde cero sin perder el historial de sesiones guardadas. Se ubica
 * en el menú lateral de escritorio y en el panel lateral móvil.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */


import React from 'react';
import { Plus } from 'lucide-react';

/**
 * Muestra el botón que inicia una consulta nueva.
 *
 * @param {object} props
 * @param {Function} props.startNewChat - Limpia la conversación activa e inicia una nueva.
 * @returns {JSX.Element} Botón «Nueva Consulta».
 */
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



