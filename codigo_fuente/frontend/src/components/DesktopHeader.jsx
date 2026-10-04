import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LogOut, Building2, ChevronDown } from 'lucide-react';
import { dbToBusinessName, INTERNAL_DB_IDS, getDbProfile } from '../constants/appConfig';
import { CompanySelector } from './CompanySelector';
import { PerfilPanel } from './PerfilPanel';
import { apiGet } from '../services/api';
import { roleLabel } from '../utils/roles';

const INTERNAL_DB_SET = new Set(INTERNAL_DB_IDS);

export function DesktopHeader({
    userAuth, connInfo, handleLogout, openQuantumCore,
    // Unificación del selector de empresa (Fase 1 — corto plazo): la insignia
    // de "Empresa Activa" deja de ser un rótulo de solo lectura y se convierte
    // en el punto de entrada al mismo CompanySelector que ya se usa en
    // "Orígenes de Datos", en vez de mantener flujos de cambio de empresa
    // distintos según la pantalla.
    availableDBs = [], fetchingDBs = false, loadDatabases, handleConnect,
}) {
    const [selectorOpen, setSelectorOpen] = useState(false);
    const popoverRef = useRef(null);
    const [perfilOpen, setPerfilOpen] = useState(false);
    const [avatarUrl, setAvatarUrl] = useState(null);

    // Se trae la foto guardada una sola vez al montar el header (no hace
    // falta esperar a abrir "Mi Perfil" para saber si el usuario ya tiene
    // avatar). Si falla (ej. token vencido), se queda con las iniciales.
    useEffect(() => {
        // Guard con `userAuth` (30/08/2026, login instantáneo): el shell puede
        // montarse de forma OPTIMISTA antes de que /login responda y exista un
        // token real. Sin este guard, este fetch salía sin Authorization,
        // fallaba en silencio (el .catch ya lo tapaba) y el avatar quedaba
        // vacío para siempre porque el efecto no reintentaba al llegar el
        // token real. Ahora se dispara recién cuando `userAuth` es real.
        if (!userAuth) return undefined;
        let cancelled = false;
        apiGet('/profile')
            .then((res) => { if (!cancelled) setAvatarUrl(res.data?.profile?.avatar || null); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [userAuth]);

    // `availableDBs` no siempre es un array de códigos de texto: cuando el
    // catálogo enriquecido (sys300) todavía no se cargó, /api/databases
    // devuelve objetos {database, business_name} crudos. Hay que extraer el
    // código y el nombre de cada forma explícitamente — nunca asignar el
    // objeto completo como si fuera el código, o React truena al intentar
    // renderizarlo como texto (bug real detectado el 2026-08-07).
    const companies = useMemo(
        () => availableDBs
            .map((entry) => {
                const isObject = entry && typeof entry === 'object';
                const code = String((isObject ? entry.database : entry) || '').trim().toUpperCase();
                if (!code) return null;
                const businessName = isObject && entry.business_name
                    ? String(entry.business_name)
                    : dbToBusinessName(code);
                return { database: code, business_name: businessName };
            })
            .filter(Boolean),
        [availableDBs]
    );

    useEffect(() => {
        if (!selectorOpen) return undefined;
        const onClickOutside = (evento) => {
            if (popoverRef.current && !popoverRef.current.contains(evento.target)) {
                setSelectorOpen(false);
            }
        };
        document.addEventListener('mousedown', onClickOutside);
        return () => document.removeEventListener('mousedown', onClickOutside);
    }, [selectorOpen]);

    const toggleSelector = () => {
        const next = !selectorOpen;
        setSelectorOpen(next);
        if (next && availableDBs.length === 0 && typeof loadDatabases === 'function') {
            loadDatabases();
        }
    };

    const seleccionarEmpresa = (dbCode) => {
        setSelectorOpen(false);
        const destino = String(dbCode || '').trim().toUpperCase();
        if (!destino || typeof handleConnect !== 'function') return;
        handleConnect(null, { ...connInfo, database: destino, selected_company_code: destino });
    };

    const selectedDb = String(connInfo?.database || '').trim().toUpperCase();
    const isChatDB = selectedDb === 'CHAT';
    const selectedCompanyCode = String(connInfo?.selected_company_code || '').trim().toUpperCase();
    const selectedCompany = selectedCompanyCode ? getDbProfile(selectedCompanyCode) : null;

    // Logica de nombre de empresa: Priorizar el nombre comercial real devuelto por SQL
    const dbProfile = getDbProfile(selectedDb);
    const companyName = dbProfile?.business_name || dbToBusinessName(selectedDb);
    const displayCompanyName = (isChatDB ? 'Mente VicMar Data AI' : (connInfo?.business_name || companyName));
    
    const showCompanyBadge = (Boolean(selectedCompanyCode) || (Boolean(selectedDb) && !INTERNAL_DB_SET.has(selectedDb))) && 
                             selectedDb !== 'MASTER' && 
                             selectedDb !== '';

    // Identidad del usuario en el header.
    //
    // La regla es no inventar identidades: mientras no se sepa quién es, no se
    // afirma nada. Se muestra un esqueleto neutro y, apenas llega `userAuth`,
    // aparece el nombre y el rol reales. (Bug del 31/08/2026: el login abría
    // el shell antes de que /login respondiera y el header rellenaba ese hueco
    // con la palabra "Analista" — alguien entraba con ADMINISTRADOR y leía un
    // perfil ajeno. Con el login actual — App.jsx > handleAuthLogin — el shell
    // se pinta con `userAuth` ya confirmado; este esqueleto solo queda como
    // red para flujos como conectar empresa o restaurar sesión.)
    const perfilListo = Boolean(userAuth?.name);
    const userLabel = userAuth?.name || '';
    const userRoleLabel = perfilListo ? roleLabel(userAuth?.role) : '';
    const initials = perfilListo
        ? userLabel.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
        : '';

    return (
        <header
            className="shrink-0 flex items-center justify-between px-6"
            style={{ height: 58, background: 'var(--bg-surface)', borderBottom: '1px solid var(--border)' }}
        >
            {/* ── Izquierda: Marca ── */}
            <div className="flex items-center gap-4 group cursor-default">
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{
                        position: 'absolute',
                        inset: -15,
                        background: 'radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 75%)',
                        borderRadius: '50%',
                        opacity: 1, filter: 'blur(8px)',
                    }} />
                    <img
                        src="/logo.png"
                        alt="Logo VicMar Data AI"
                        style={{
                            width: 44, height: 44, objectFit: 'contain',
                            filter: 'brightness(1.5) contrast(1.2) drop-shadow(0 0 15px rgba(59,130,246,0.7))',
                            transition: 'all 0.4s ease', zIndex: 1
                        }}
                    />
                </div>
                <span style={{
                    fontWeight: 800, fontSize: 24, color: 'var(--text-primary)',
                    letterSpacing: '-0.03em', fontFamily: "'Outfit', sans-serif",
                    background: 'linear-gradient(to bottom, #fff 0%, #cbd5e1 100%)',
                    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
                }}>
                    VicMar&nbsp;&nbsp;Data AI
                </span>
            </div>

            {/* ── Derecha: Contexto y Usuario ── */}
            <div className="flex items-center gap-6">
                {/* Visualizador de Empresa Activa — ahora es también el único punto
                    de entrada para cambiar de empresa desde el dashboard de
                    escritorio (antes había que ir a "Orígenes de Datos"). */}
                {showCompanyBadge && (
                    <div ref={popoverRef} className="relative">
                        <button
                            type="button"
                            onClick={toggleSelector}
                            aria-haspopup="dialog"
                            aria-expanded={selectorOpen}
                            aria-label="Cambiar empresa activa"
                            title="Cambiar empresa"
                            className="flex items-center gap-3 transition-colors hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                            style={{
                                padding: '6px 14px 6px 18px',
                                background: 'rgba(34, 211, 238, 0.05)',
                                border: '1px solid rgba(34, 211, 238, 0.2)',
                                borderRadius: 16,
                                boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
                                overflow: 'hidden',
                                cursor: 'pointer',
                            }}
                        >
                            <Building2 size={14} className="text-cyan-400" aria-hidden="true" />
                            <div className="flex flex-col items-start">
                                <span style={{ fontSize: 11, fontWeight: 900, color: 'rgba(34, 211, 238, 0.6)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: 1 }}>
                                    Empresa Activa
                                </span>
                                {/* Solo el nombre comercial real de la empresa — nunca el código
                                    interno de la base (ej. "SONG"), que es un identificador
                                    técnico del ingeniero de bases, no el nombre de la empresa
                                    (2026-09-08). */}
                                <span style={{ fontSize: 13, fontWeight: 800, color: '#fff', letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>
                                    {displayCompanyName}
                                </span>
                            </div>
                            <ChevronDown
                                size={14}
                                className="text-cyan-400/60 transition-transform"
                                style={{ transform: selectorOpen ? 'rotate(180deg)' : 'none' }}
                                aria-hidden="true"
                            />
                        </button>

                        {selectorOpen && (
                            <div className="absolute right-0 z-50 mt-2 w-96">
                                <CompanySelector
                                    companies={companies}
                                    activeDb={connInfo?.database}
                                    onSelect={seleccionarEmpresa}
                                    disabled={fetchingDBs}
                                    autoOpen
                                    hideTrigger
                                    onRequestClose={() => setSelectorOpen(false)}
                                />
                            </div>
                        )}
                    </div>
                )}

                <div className="flex items-center gap-4">
                    {/* Avatar + nombre — abre "Mi Perfil" (Fase 5, 28/08/2026,
                        por requisito: antes esto era solo una etiqueta,
                        sin ninguna accion al hacer clic). */}
                    <button
                        type="button"
                        onClick={() => setPerfilOpen(true)}
                        aria-haspopup="dialog"
                        aria-expanded={perfilOpen}
                        aria-label="Abrir Mi Perfil"
                        title="Mi Perfil"
                        className="flex items-center gap-2 rounded-lg transition-opacity hover:opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/50"
                    >
                        <div style={{
                            width: 36, height: 36, borderRadius: '50%',
                            background: 'var(--accent)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 14, fontWeight: 700, color: 'white', flexShrink: 0,
                            border: '1px solid rgba(255,255,255,0.1)',
                            overflow: 'hidden',
                        }}>
                            {avatarUrl ? (
                                <img src={avatarUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            ) : (
                                initials
                            )}
                        </div>
                        <div className="hidden md:flex flex-col items-start">
                            {perfilListo ? (
                                <>
                                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2 }}>{userLabel}</span>
                                    <span style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{userRoleLabel}</span>
                                </>
                            ) : (
                                /* Esqueleto mientras /login confirma quién es. Mismas alturas
                                   que el nombre y el rol reales, para que al llegar el dato no
                                   se mueva nada alrededor. */
                                <span aria-label="Cargando perfil" className="flex flex-col items-start gap-1 py-0.5">
                                    <span style={{ display: 'block', width: 72, height: 9, borderRadius: 4, background: 'var(--border)', opacity: 0.7 }} />
                                    <span style={{ display: 'block', width: 46, height: 7, borderRadius: 4, background: 'var(--border)', opacity: 0.45 }} />
                                </span>
                            )}
                        </div>
                    </button>

                    <div style={{ width: 1, height: 24, background: 'var(--border)', opacity: 0.5 }} />

                    {/* Desconectar */}
                    <button
                        onClick={() => handleLogout()}
                        className="flex items-center gap-1.5 hover:brightness-110 active:scale-95 transition-all"
                        style={{
                            fontSize: 11, fontWeight: 600, color: 'var(--danger)',
                            background: 'var(--danger-subtle)', border: '1px solid var(--danger-border)',
                            borderRadius: 8, padding: '6px 14px', cursor: 'pointer',
                        }}
                    >
                        <LogOut size={12} />
                        <span className="hidden md:inline">Desconectar</span>
                    </button>
                </div>
            </div>

            <PerfilPanel
                open={perfilOpen}
                onClose={() => setPerfilOpen(false)}
                userAuth={userAuth}
                avatarUrl={avatarUrl}
                onAvatarChange={setAvatarUrl}
            />
        </header>
    );
}
