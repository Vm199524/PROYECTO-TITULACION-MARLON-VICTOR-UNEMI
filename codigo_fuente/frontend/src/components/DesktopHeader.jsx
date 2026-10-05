/**
 * @file Cabecera del panel de escritorio. Muestra la marca, la insignia «Empresa Activa»
 * (que abre CompanySelector para cambiar de base), el avatar con el nombre y el rol del
 * usuario (que abre PerfilPanel) y el botón para desconectar. Lee la foto de perfil de
 * /api/profile.
 * @author Marlon David Pérez Almachi
 * @author Víctor Manuel Lluilema Pisco
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LogOut, Building2, ChevronDown } from 'lucide-react';
import { dbToBusinessName, INTERNAL_DB_IDS, getDbProfile } from '../constants/appConfig';
import { CompanySelector } from './CompanySelector';
import { PerfilPanel } from './PerfilPanel';
import { apiGet } from '../services/api';
import { roleLabel } from '../utils/roles';

const INTERNAL_DB_SET = new Set(INTERNAL_DB_IDS);

/**
 * Muestra la cabecera superior del panel de escritorio.
 *
 * @param {object} props
 * @param {object|null} props.userAuth - Usuario autenticado (`name`, `role`); null mientras se confirma.
 * @param {object} props.connInfo - Conexión activa (`database`, `selected_company_code`, `business_name`).
 * @param {Function} props.handleLogout - Cierra la sesión.
 * @param {Function} [props.openQuantumCore] - Se recibe, pero esta cabecera no lo usa.
 * @param {Array<string|object>} [props.availableDBs=[]] - Bases disponibles, como códigos o como objetos `{database, business_name}`.
 * @param {boolean} [props.fetchingDBs=false] - Si la lista de bases se está cargando.
 * @param {Function} [props.loadDatabases] - Carga la lista de bases al abrir el selector si aún está vacía.
 * @param {Function} props.handleConnect - Reconecta con la empresa elegida.
 * @returns {JSX.Element} Cabecera del panel.
 */
export function DesktopHeader({
    userAuth, connInfo, handleLogout, openQuantumCore,
    // La insignia «Empresa Activa» es el punto de entrada al mismo
    // CompanySelector de «Orígenes de Datos», para no mantener flujos de
    // cambio de empresa distintos según la pantalla.
    availableDBs = [], fetchingDBs = false, loadDatabases, handleConnect,
}) {
    const [selectorOpen, setSelectorOpen] = useState(false);
    const popoverRef = useRef(null);
    const [perfilOpen, setPerfilOpen] = useState(false);
    const [avatarUrl, setAvatarUrl] = useState(null);

    // Se trae la foto guardada al montar la cabecera, sin esperar a que se abra
    // «Mi Perfil». Si falla (p. ej. token vencido), se muestran las iniciales.
    useEffect(() => {
        // El shell puede montarse de forma optimista antes de que /login
        // responda y exista un token real. Sin esta guarda, la petición saldría
        // sin Authorization, fallaría en silencio y el avatar quedaría vacío.
        // Por eso se dispara solo cuando `userAuth` existe.
        if (!userAuth) return undefined;
        let cancelled = false;
        apiGet('/profile')
            .then((res) => { if (!cancelled) setAvatarUrl(res.data?.profile?.avatar || null); })
            .catch(() => {});
        return () => { cancelled = true; };
    }, [userAuth]);

    // `availableDBs` no siempre es un arreglo de códigos de texto: cuando el
    // catálogo enriquecido (sys300) todavía no se cargó, /api/databases
    // devuelve objetos {database, business_name} crudos. Se extraen el código
    // y el nombre de cada forma explícitamente; asignar el objeto completo
    // como si fuera el código hace fallar a React al renderizarlo como texto.
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

    // Nombre de la empresa: se prioriza el nombre comercial real que devuelve la
    // conexión o el catálogo sobre el derivado del código de la base.
    const dbProfile = getDbProfile(selectedDb);
    const companyName = dbProfile?.business_name || dbToBusinessName(selectedDb);
    const displayCompanyName = (isChatDB ? 'Mente VicMar Data AI' : (connInfo?.business_name || companyName));
    
    const showCompanyBadge = (Boolean(selectedCompanyCode) || (Boolean(selectedDb) && !INTERNAL_DB_SET.has(selectedDb))) && 
                             selectedDb !== 'MASTER' && 
                             selectedDb !== '';

    // Identidad del usuario en la cabecera.
    //
    // No se inventan identidades: mientras no se sepa quién es el usuario, se
    // muestra un esqueleto neutro y, al llegar `userAuth`, el nombre y el rol
    // reales. Rellenar el hueco con un rol por defecto (p. ej. «Analista»)
    // mostraría un perfil ajeno a quien entra como ADMINISTRADOR. El login de
    // App.jsx (handleAuthLogin) ya pinta el shell con `userAuth` confirmado; el
    // esqueleto cubre flujos como conectar empresa o restaurar sesión.
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
                {/* Insignia de la empresa activa: también es el punto de entrada
                    para cambiar de empresa desde el panel de escritorio. */}
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
                                {/* Solo el nombre comercial de la empresa, nunca el código
                                    interno de la base (p. ej. «SONG»), que es un
                                    identificador técnico y no el nombre de la empresa. */}
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
                    {/* Avatar y nombre: abre «Mi Perfil». */}
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
                                /* Esqueleto mientras /login confirma la identidad. Tiene las
                                   mismas alturas que el nombre y el rol reales, para que al
                                   llegar el dato no se mueva nada alrededor. */
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
