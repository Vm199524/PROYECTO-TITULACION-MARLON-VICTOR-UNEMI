import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Building2, Check, ChevronDown, Loader2, Search } from 'lucide-react';

/**
 * Selector de empresa tipo "combobox buscable" (patrón command-palette).
 *
 * Reemplaza la cuadrícula de 22 botones fijos que había antes. Con esa
 * cantidad de empresas, una cuadrícula obliga a barrer visualmente toda la
 * pantalla para encontrar una; escribir tres letras es mucho más rápido.
 * Es el patrón que usan Linear, Vercel, Stripe y GitHub para cambiar de
 * organización/proyecto.
 *
 * Accesibilidad: implementa el rol `combobox` con `listbox` asociado,
 * navegación con flechas, Enter para elegir y Escape para cerrar.
 */
export function CompanySelector({
    companies = [],
    activeDb = '',
    switchingDb = '',
    onSelect,
    disabled = false,
    // Cuando este selector se abre dentro de un popover que ya fue activado
    // por otro control (p. ej. la insignia de "Empresa activa" en la
    // cabecera), no tiene sentido pedirle al usuario un segundo clic para
    // desplegar la lista: nace ya abierto.
    autoOpen = false,
    // Oculta el botón disparador propio de este componente cuando ya vive
    // dentro de un popover controlado por otro trigger externo (evita mostrar
    // dos pastillas "Empresa activa" apiladas). El panel de búsqueda/lista
    // se muestra directamente.
    hideTrigger = false,
    // Se invoca al elegir una empresa o al cerrar con Escape, para que el
    // contenedor externo (si existe) también se cierre.
    onRequestClose,
}) {
    const [abierto, setAbierto] = useState(autoOpen);
    const [busqueda, setBusqueda] = useState('');
    const [indiceResaltado, setIndiceResaltado] = useState(0);

    const contenedorRef = useRef(null);
    const inputRef = useRef(null);
    const listaRef = useRef(null);

    const activo = String(activeDb || '').trim().toUpperCase();
    const cambiando = String(switchingDb || '').trim().toUpperCase();

    const ordenadas = useMemo(
        () => [...companies].sort((a, b) =>
            (a.business_name || a.database || '').localeCompare(b.business_name || b.database || '')
        ),
        [companies]
    );

    const filtradas = useMemo(() => {
        const q = busqueda.trim().toLowerCase();
        if (!q) return ordenadas;
        // Busca tanto por código de base (GYMJ) como por nombre comercial
        // (AGRINAG), porque el usuario puede recordar cualquiera de los dos.
        return ordenadas.filter((c) =>
            `${c.database || ''} ${c.business_name || ''}`.toLowerCase().includes(q)
        );
    }, [ordenadas, busqueda]);

    const empresaActiva = ordenadas.find(
        (c) => String(c.database || '').toUpperCase() === activo
    );

    // Cerrar al hacer clic fuera
    useEffect(() => {
        if (!abierto) return undefined;
        const alClicFuera = (evento) => {
            if (contenedorRef.current && !contenedorRef.current.contains(evento.target)) {
                setAbierto(false);
            }
        };
        document.addEventListener('mousedown', alClicFuera);
        return () => document.removeEventListener('mousedown', alClicFuera);
    }, [abierto]);

    // Al abrir: foco en el buscador y reinicio del filtro
    useEffect(() => {
        if (abierto) {
            setBusqueda('');
            setIndiceResaltado(0);
            const id = setTimeout(() => inputRef.current?.focus(), 30);
            return () => clearTimeout(id);
        }
        return undefined;
    }, [abierto]);

    // Mantener visible la opción resaltada al navegar con flechas
    useEffect(() => {
        if (!abierto || !listaRef.current) return;
        const elemento = listaRef.current.querySelector(`[data-indice="${indiceResaltado}"]`);
        elemento?.scrollIntoView({ block: 'nearest' });
    }, [indiceResaltado, abierto]);

    const elegir = (empresa) => {
        if (!empresa || disabled) return;
        setAbierto(false);
        onSelect?.(empresa.database);
        onRequestClose?.();
    };

    const alPresionarTecla = (evento) => {
        if (evento.key === 'ArrowDown') {
            evento.preventDefault();
            setIndiceResaltado((i) => Math.min(i + 1, filtradas.length - 1));
        } else if (evento.key === 'ArrowUp') {
            evento.preventDefault();
            setIndiceResaltado((i) => Math.max(i - 1, 0));
        } else if (evento.key === 'Enter') {
            evento.preventDefault();
            elegir(filtradas[indiceResaltado]);
        } else if (evento.key === 'Escape') {
            evento.preventDefault();
            setAbierto(false);
            onRequestClose?.();
        }
    };

    const etiquetaActual = empresaActiva
        ? `${empresaActiva.database} — ${empresaActiva.business_name || empresaActiva.database}`
        : (activo || 'Selecciona una empresa');

    const panel = (
        <div
            className={
                hideTrigger
                    ? 'w-full overflow-hidden rounded-2xl border border-white/10 bg-[#0d1117] shadow-2xl'
                    : 'absolute z-50 mt-2 w-full overflow-hidden rounded-2xl border border-white/10 bg-[#0d1117] shadow-2xl'
            }
        >
                    <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
                        <Search size={15} className="shrink-0 text-white/30" aria-hidden="true" />
                        <input
                            ref={inputRef}
                            value={busqueda}
                            onChange={(e) => { setBusqueda(e.target.value); setIndiceResaltado(0); }}
                            onKeyDown={alPresionarTecla}
                            placeholder="Buscar por código o nombre…"
                            aria-label="Buscar empresa"
                            aria-controls="lista-empresas"
                            className="w-full bg-transparent text-[14px] text-white outline-none placeholder:text-white/25"
                        />
                        <span className="shrink-0 text-[11px] font-bold text-white/25">
                            {filtradas.length}
                        </span>
                    </div>

                    <ul
                        ref={listaRef}
                        id="lista-empresas"
                        role="listbox"
                        aria-label="Empresas disponibles"
                        className="max-h-[320px] overflow-y-auto py-1 custom-scrollbar"
                    >
                        {filtradas.length === 0 && (
                            <li className="px-5 py-6 text-center text-[13px] text-white/35">
                                Ninguna empresa coincide con «{busqueda}»
                            </li>
                        )}

                        {filtradas.map((empresa, indice) => {
                            const codigo = String(empresa.database || '').toUpperCase();
                            const esActiva = codigo === activo;
                            const estaCambiando = codigo === cambiando;
                            const resaltada = indice === indiceResaltado;

                            return (
                                <li key={codigo} role="none">
                                    <button
                                        type="button"
                                        data-indice={indice}
                                        role="option"
                                        aria-selected={esActiva}
                                        onMouseEnter={() => setIndiceResaltado(indice)}
                                        onClick={() => elegir(empresa)}
                                        className={`flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors ${
                                            resaltada ? 'bg-cyan-500/10' : ''
                                        }`}
                                    >
                                        <span className="flex min-w-0 flex-col">
                                            <span className={`truncate text-[14px] font-semibold ${esActiva ? 'text-cyan-300' : 'text-white/80'}`}>
                                                {empresa.business_name || empresa.database}
                                            </span>
                                            <span className="text-[12px] text-white/35">{empresa.database}</span>
                                        </span>

                                        <span className="shrink-0">
                                            {estaCambiando ? (
                                                <Loader2 size={15} className="animate-spin text-cyan-400" aria-hidden="true" />
                                            ) : esActiva ? (
                                                <Check size={15} className="text-cyan-400" aria-hidden="true" />
                                            ) : null}
                                        </span>
                                    </button>
                                </li>
                            );
                        })}
                    </ul>

            <div className="border-t border-white/5 px-5 py-2.5 text-[11px] text-white/25">
                ↑↓ navegar · Enter seleccionar · Esc cerrar
            </div>
        </div>
    );

    if (hideTrigger) {
        // El disparador vive fuera (p. ej. la insignia de la cabecera);
        // aquí solo se entrega el panel de búsqueda/lista, ya abierto.
        return <div ref={contenedorRef} className="w-full">{panel}</div>;
    }

    return (
        <div ref={contenedorRef} className="relative w-full">
            <button
                type="button"
                onClick={() => !disabled && setAbierto((v) => !v)}
                disabled={disabled}
                role="combobox"
                aria-expanded={abierto}
                aria-haspopup="listbox"
                aria-label="Seleccionar empresa"
                className={`flex w-full items-center justify-between gap-3 rounded-2xl border px-5 py-4 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50 ${
                    abierto
                        ? 'border-cyan-500/40 bg-cyan-500/[0.06]'
                        : 'border-white/10 bg-white/[0.03] hover:border-cyan-500/25'
                } ${disabled ? 'cursor-not-allowed opacity-50' : ''}`}
            >
                <span className="flex min-w-0 items-center gap-3">
                    <Building2 size={17} className="shrink-0 text-cyan-400" aria-hidden="true" />
                    <span className="min-w-0">
                        <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-white/35">
                            Empresa activa
                        </span>
                        <span className="block truncate text-[15px] font-bold text-white">
                            {etiquetaActual}
                        </span>
                    </span>
                </span>

                <span className="flex shrink-0 items-center gap-2">
                    {cambiando && (
                        <Loader2 size={15} className="animate-spin text-cyan-400" aria-hidden="true" />
                    )}
                    <ChevronDown
                        size={17}
                        className={`text-white/40 transition-transform ${abierto ? 'rotate-180' : ''}`}
                        aria-hidden="true"
                    />
                </span>
            </button>

            {abierto && panel}
        </div>
    );
}
