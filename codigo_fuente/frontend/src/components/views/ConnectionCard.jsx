/**
 * ConnectionCard.jsx — Tarjeta visual de conexión al servidor SQL.
 *
 * Responsabilidades (únicas):
 *   1. Formulario de conexión: host, auth, credenciales, driver ODBC.
 *   2. Botones de acción: Conectar, Cancelar, Explorar, Catálogo.
 *   3. Estado de UI local: show/hide password, dropdown de servidores
 *      recientes, carga de drivers ODBC desde el backend.
 *   4. Panel de bases descubiertas con CompanySelector.
 *
 * Todo el estado de negocio (isConnecting, connectError, companies,
 * switchingDatabase, etc.) viene de DataChannels como props.
 * Este componente NO dispara peticiones de negocio por cuenta propia.
 *
 * Extraído de DataChannels.jsx (27/07/2026) para reducir ese archivo
 * de ~870 líneas a <220 líneas de orquestación pura.
 */
import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
    Check,
    ChevronDown,
    Clock,
    Database,
    Eye,
    EyeOff,
    Key,
    Loader2,
    Plug,
    RefreshCw,
    Server,
    Shield,
    User,
    Wifi,
    WifiOff,
    X,
    Zap,
} from 'lucide-react';

import { CompanySelector } from '../CompanySelector';
import { apiGet } from '../../services/api';
import { normalizeSqlServerHost } from '../../utils/sqlServer';

export function ConnectionCard({
    connInfo = {},
    recentServers = [],
    knownServers = [],
    onSelectKnownServer,
    isConnecting = false,
    connectError = '',
    connectSuccess = false,
    fetchingDBs = false,
    fetchingCompanies = false,
    discoveredDatabases = [],
    companyRows = [],
    switchingDatabase = '',
    onFieldChange,
    onAuthTypeChange,
    onConnect,
    onCancel,
    onExplore,
    onLoadCatalog,
    onSelectDatabase,
}) {
    // ── Estado local de UI (no sube a DataChannels) ───────────────────
    const [showPassword, setShowPassword] = useState(false);
    const [showRecentServers, setShowRecentServers] = useState(false);
    const [availableDrivers, setAvailableDrivers] = useState([]);
    const [recommendedDriver, setRecommendedDriver] = useState('');

    const serverInputRef = useRef(null);
    const recentDropdownRef = useRef(null);

    // Cargar drivers ODBC disponibles desde el backend al montar
    useEffect(() => {
        apiGet('/drivers').then(res => {
            if (res.data?.drivers?.length > 0) {
                setAvailableDrivers(res.data.drivers);
                setRecommendedDriver(res.data.recommended || '');
                if (!connInfo.driver || connInfo.driver === 'AUTO') {
                    onFieldChange?.('driver', res.data.recommended || res.data.drivers[0]);
                }
            }
        }).catch(() => { /* silent */ });
    }, []);

    // Cerrar dropdown de recientes si se hace click afuera
    useEffect(() => {
        const handler = (e) => {
            if (recentDropdownRef.current && !recentDropdownRef.current.contains(e.target)) {
                setShowRecentServers(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // ── Derived values ────────────────────────────────────────────────
    const isConnected = Boolean(connInfo.host);
    const authMode = String(connInfo.auth_type || '').trim();
    const showSqlCredentialFields = authMode !== 'Windows Authentication';
    const hostLabel = String(connInfo.host || '').trim() || 'Sin configurar';

    return (
        <div className="relative shadow-2xl group">
            {/* Fondo Bento Independiente (Sin recortes por overflow) */}
            <div className="absolute inset-0 rounded-[32px] border border-cyan-500/20 bg-gradient-to-br from-[#0a1628] via-[#070f1e] to-[#050b18] -z-10 shadow-2xl" />

            {/* ── Card Header ─────────────────────────────────────────── */}
            <div className="flex items-center gap-4 px-6 py-4 border-b border-white/[0.06]">
                <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20">
                    <Server size={22} className="text-cyan-400" />
                </div>
                <div className="flex-1 min-w-0">
                    <h2 className="text-white font-bold text-base">Conectar con el servidor</h2>
                    <p className="text-xs text-white/40 truncate mt-0.5">
                        {isConnected ? (
                            <span className="flex items-center gap-1.5 text-emerald-400">
                                <Wifi size={11} />
                                {hostLabel}
                            </span>
                        ) : (
                            <span className="flex items-center gap-1.5">
                                <WifiOff size={11} />
                                Sin conexión activa
                            </span>
                        )}
                    </p>
                </div>
                {isConnected && (
                    <div className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-1.5 mr-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Online
                    </div>
                )}
            </div>

            {/* ── Connection Form ──────────────────────────────────────── */}
            <div className="px-6 py-5 space-y-3">

                {/* Row 1: Tipo de servidor */}
                <div>
                    <label className="flex items-center gap-2 mb-2 text-[12px] font-black uppercase tracking-[0.22em] text-white/35">
                        <Database size={11} />
                        Tipo de servidor
                    </label>
                    <select className="w-full h-11 px-4 rounded-xl bg-black/40 border border-white/10 text-sm text-white outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all appearance-none cursor-pointer">
                        <option value="database">Motor de base de datos</option>
                    </select>
                </div>

                {/* Row 2: Nombre del servidor */}
                <div>
                    <label className="flex items-center gap-2 mb-2 text-[12px] font-black uppercase tracking-[0.22em] text-white/35">
                        <Server size={11} />
                        Nombre del servidor
                    </label>
                    <div className="relative" ref={recentDropdownRef}>
                        <input
                            ref={serverInputRef}
                            type="text"
                            value={connInfo.host || ''}
                            onChange={(e) => onFieldChange?.('host', e.target.value)}
                            onBlur={(e) => onFieldChange?.('host', normalizeSqlServerHost(e.target.value))}
                            onFocus={() => (knownServers.length > 0 || recentServers.length > 0) && setShowRecentServers(true)}
                            onKeyDown={(e) => { if (e.key === 'Enter') onConnect?.(); }}
                            placeholder="SERVIDOR, localhost, 192.168.1.100,1433, HOST\INSTANCIA"
                            className="w-full h-12 pl-4 pr-10 rounded-xl bg-black/40 border border-white/10 text-sm text-white placeholder:text-white/25 outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all"
                        />
                        <button
                            type="button"
                            onClick={() => setShowRecentServers(v => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-cyan-300 transition-colors"
                            title="Servidores recientes"
                        >
                            <ChevronDown size={16} />
                        </button>

                        {/* Servidores disponibles (catálogo autorizado) + recientes */}
                        <AnimatePresence>
                            {showRecentServers && (knownServers.length > 0 || recentServers.length > 0) && (
                                <motion.div
                                    initial={{ opacity: 0, y: -8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    className="absolute z-50 top-full mt-1 left-0 right-0 rounded-xl bg-[#0d1a2e] border border-white/10 shadow-2xl overflow-hidden max-h-72 overflow-y-auto"
                                >
                                    {knownServers.length > 0 && (
                                        <>
                                            <div className="px-3 pt-2 pb-1 text-[11px] font-black uppercase tracking-[0.2em] text-emerald-400/70 flex items-center gap-1.5">
                                                <Database size={9} />
                                                Servidores disponibles
                                            </div>
                                            {knownServers.map((srv) => (
                                                <button
                                                    key={srv.id || srv.host}
                                                    type="button"
                                                    onClick={() => {
                                                        onSelectKnownServer?.(srv);
                                                        setShowRecentServers(false);
                                                    }}
                                                    title={srv.notes || ''}
                                                    className="w-full flex items-start gap-3 px-3 py-2.5 text-sm text-white/70 hover:bg-emerald-500/10 hover:text-white transition-colors text-left"
                                                >
                                                    <Database size={13} className="text-emerald-400/70 shrink-0 mt-0.5" />
                                                    <span className="min-w-0">
                                                        <span className="block truncate">{srv.label || srv.host}</span>
                                                        <span className="block text-[11px] text-white/35 truncate">{srv.host} · {srv.environment || 'DEV'}</span>
                                                    </span>
                                                </button>
                                            ))}
                                        </>
                                    )}
                                    {recentServers.length > 0 && (
                                        <>
                                            <div className="px-3 pt-2 pb-1 text-[11px] font-black uppercase tracking-[0.2em] text-white/30 flex items-center gap-1.5">
                                                <Clock size={9} />
                                                Recientes
                                            </div>
                                            {recentServers.map((srv) => (
                                                <button
                                                    key={srv}
                                                    type="button"
                                                    onClick={() => {
                                                        onFieldChange?.('host', srv);
                                                        setShowRecentServers(false);
                                                    }}
                                                    className="w-full flex items-center gap-3 px-3 py-2.5 text-sm text-white/70 hover:bg-cyan-500/10 hover:text-white transition-colors"
                                                >
                                                    <Server size={13} className="text-cyan-400/60 shrink-0" />
                                                    <span className="truncate">{srv}</span>
                                                </button>
                                            ))}
                                        </>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                {/* Row 3: Autenticación */}
                <div>
                    <label className="flex items-center gap-2 mb-2 text-[12px] font-black uppercase tracking-[0.22em] text-white/35">
                        <Shield size={11} />
                        Autenticación
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        {[
                            { value: 'Windows Authentication', label: 'Autenticación de Windows', icon: Shield },
                            { value: 'SQL Server Authentication', label: 'Autenticación de SQL Server', icon: Key },
                        ].map(({ value, label, icon: Icon }) => (
                            <button
                                key={value}
                                type="button"
                                onClick={() => onAuthTypeChange?.(value)}
                                className={`flex items-center gap-3 px-4 py-3 rounded-xl border text-left text-sm transition-all ${authMode === value
                                    ? 'border-cyan-400/50 bg-cyan-500/10 text-cyan-100'
                                    : 'border-white/10 bg-black/30 text-white/60 hover:border-white/20 hover:text-white/80'
                                    }`}
                            >
                                <Icon size={15} className={authMode === value ? 'text-cyan-400' : 'text-white/40'} />
                                <span className="text-xs font-semibold leading-tight">{label}</span>
                                {authMode === value && <Check size={13} className="ml-auto text-cyan-400 shrink-0" />}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Row 4: Credenciales SQL (condicional) */}
                <AnimatePresence>
                    {showSqlCredentialFields && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="overflow-hidden"
                        >
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="flex items-center gap-2 mb-2 text-[12px] font-black uppercase tracking-[0.22em] text-white/35">
                                        <User size={11} />
                                        Nombre de usuario
                                    </label>
                                    <input
                                        type="text"
                                        value={connInfo.user || ''}
                                        onChange={(e) => onFieldChange?.('user', e.target.value)}
                                        placeholder="sa"
                                        className="w-full h-11 px-4 rounded-xl bg-black/40 border border-white/10 text-sm text-white placeholder:text-white/25 outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="flex items-center gap-2 mb-2 text-[12px] font-black uppercase tracking-[0.22em] text-white/35">
                                        <Key size={11} />
                                        Contraseña
                                    </label>
                                    <div className="relative">
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            value={connInfo.password || ''}
                                            onChange={(e) => onFieldChange?.('password', e.target.value)}
                                            onKeyDown={(e) => { if (e.key === 'Enter') onConnect?.(); }}
                                            placeholder="••••••••"
                                            className="w-full h-11 pl-4 pr-11 rounded-xl bg-black/40 border border-white/10 text-sm text-white placeholder:text-white/25 outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/20 transition-all"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(v => !v)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/35 hover:text-white/70 transition-colors"
                                        >
                                            {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Row 5: Driver ODBC (colapsado por defecto) */}
                <details className="group">
                    <summary className="flex items-center gap-2 cursor-pointer text-[12px] font-black uppercase tracking-[0.22em] text-white/30 hover:text-white/50 transition-colors select-none list-none">
                        <ChevronDown size={11} className="group-open:rotate-180 transition-transform" />
                        Opciones avanzadas (Driver ODBC)
                    </summary>
                    <div className="mt-3">
                        {availableDrivers.length > 0 ? (
                            <>
                                <select
                                    value={connInfo.driver || ''}
                                    onChange={(e) => onFieldChange?.('driver', e.target.value)}
                                    className="w-full h-11 px-4 rounded-xl bg-black/40 border border-white/10 text-sm text-white outline-none focus:border-cyan-400/50 transition-all appearance-none cursor-pointer"
                                >
                                    {Array.from(new Set([
                                        'SQL Server',
                                        'ODBC Driver 17 for SQL Server',
                                        'ODBC Driver 18 for SQL Server',
                                        ...(availableDrivers || []),
                                        'SQL Server Native Client 11.0',
                                    ])).map(d => (
                                        <option key={d} value={d}>
                                            {d} {d === 'SQL Server' ? '✓ (Recomendado)' : (d === recommendedDriver ? '(Detectado)' : '')}
                                        </option>
                                    ))}
                                </select>
                                <p className="mt-1.5 text-[11px] text-white/25">
                                    Ecosistema VicMar Data AI: Resolución inteligente de drivers activa.
                                </p>
                            </>
                        ) : (
                            <select
                                value={connInfo.driver || ''}
                                onChange={(e) => onFieldChange?.('driver', e.target.value)}
                                className="w-full h-11 px-4 rounded-xl bg-black/40 border border-white/10 text-sm text-white outline-none focus:border-cyan-400/50 transition-all appearance-none cursor-pointer"
                            >
                                <option value="">-- Seleccionar Driver --</option>
                                <option value="ODBC Driver 17 for SQL Server">ODBC Driver 17 for SQL Server</option>
                                <option value="ODBC Driver 13 for SQL Server">ODBC Driver 13 for SQL Server</option>
                                <option value="ODBC Driver 18 for SQL Server">ODBC Driver 18 for SQL Server</option>
                                <option value="SQL Server Native Client 11.0">SQL Server Native Client 11.0</option>
                                <option value="SQL Server">SQL Server (Legacy)</option>
                            </select>
                        )}
                    </div>
                </details>

                {/* Error / Success feedback */}
                <AnimatePresence>
                    {connectError && (
                        <motion.div
                            initial={{ opacity: 0, y: -6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300"
                        >
                            <WifiOff size={14} className="shrink-0 mt-0.5" />
                            <span>{connectError}</span>
                        </motion.div>
                    )}
                    {connectSuccess && !connectError && (
                        <motion.div
                            initial={{ opacity: 0, y: -6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-300"
                        >
                            <Wifi size={14} className="shrink-0" />
                            <span>Conexión establecida con <strong>{connInfo.host}</strong></span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── Action buttons ──────────────────────────────────── */}
                <div className="flex gap-3 pt-1">

                    {/* SPLIT BUTTON: Conectar ║ Cancelar */}
                    <div
                        className="flex-1 flex h-12 rounded-xl overflow-hidden shadow-lg"
                        style={{
                            boxShadow: isConnecting
                                ? '0 0 0 1.5px rgba(239,68,68,0.4), 0 4px 20px rgba(239,68,68,0.2)'
                                : '0 0 0 1px rgba(34,211,238,0.25), 0 4px 20px rgba(34,211,238,0.12)',
                            transition: 'box-shadow 0.25s ease',
                        }}
                    >
                        <button
                            type="button"
                            onClick={!isConnecting ? onConnect : undefined}
                            disabled={isConnecting}
                            className={`flex flex-1 items-center justify-center gap-2.5 text-white text-sm font-bold uppercase tracking-[0.15em] transition-all duration-200 ${isConnecting
                                ? 'bg-gradient-to-r from-cyan-700/60 to-blue-800/60 cursor-not-allowed'
                                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 cursor-pointer'
                                }`}
                        >
                            {isConnecting ? (
                                <><Loader2 size={15} className="animate-spin opacity-80" />
                                    <span className="opacity-80">Conectando...</span></>
                            ) : (
                                <><Plug size={15} /> Conectar</>
                            )}
                        </button>

                        <div
                            className="w-px self-stretch transition-colors duration-200"
                            style={{ background: isConnecting ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.15)' }}
                        />

                        <button
                            type="button"
                            onClick={isConnecting ? onCancel : undefined}
                            disabled={!isConnecting}
                            title={isConnecting ? 'Cancelar conexión' : 'Disponible al conectar'}
                            className={`flex items-center justify-center gap-1.5 px-5 text-xs font-bold uppercase tracking-[0.12em] transition-all duration-200 ${isConnecting
                                ? 'bg-red-600 hover:bg-red-500 text-white cursor-pointer'
                                : 'bg-red-950/60 text-red-400/25 cursor-not-allowed'
                                }`}
                        >
                            <X size={13} />
                            <span>Cancelar</span>
                        </button>
                    </div>

                    {/* SECONDARY: Explorar Bases */}
                    <div className="relative group/exp">
                        <button
                            type="button"
                            onClick={onExplore}
                            disabled={fetchingDBs || !connInfo.host}
                            className="flex items-center gap-2 px-4 h-12 rounded-xl border border-white/10 bg-white/[0.04] text-white/70 hover:text-white hover:border-white/20 text-xs font-bold uppercase tracking-[0.15em] transition-all disabled:opacity-40 whitespace-nowrap"
                        >
                            {fetchingDBs ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                            Explorar
                        </button>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/exp:block z-50 w-56 rounded-lg bg-[#0d1a2e] border border-white/10 p-3 shadow-xl text-left pointer-events-none">
                            <div className="text-[12px] font-black uppercase tracking-wider text-cyan-300 mb-1">Explorar Bases</div>
                            <div className="text-[12px] text-white/55 leading-relaxed">
                                Ejecuta <code className="text-cyan-300">SELECT name FROM sys.databases</code> — Lista <strong>todas</strong> las bases físicas del servidor, sin filtros.
                            </div>
                        </div>
                    </div>

                    {/* TERTIARY: Catálogo de Empresas */}
                    <div className="relative group/cat">
                        <button
                            type="button"
                            onClick={onLoadCatalog}
                            disabled={fetchingCompanies || !connInfo.host}
                            className="flex items-center gap-2 px-4 h-12 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.07] text-emerald-300 hover:text-emerald-200 hover:border-emerald-400/40 text-xs font-bold uppercase tracking-[0.15em] transition-all disabled:opacity-40 whitespace-nowrap"
                        >
                            {fetchingCompanies ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                            Catálogo
                        </button>
                        <div className="absolute bottom-full right-0 mb-2 hidden group-hover/cat:block z-50 w-64 rounded-lg bg-[#0d1a2e] border border-white/10 p-3 shadow-xl text-left pointer-events-none">
                            <div className="text-[12px] font-black uppercase tracking-wider text-emerald-300 mb-1">Catálogo Maestro</div>
                            <div className="text-[12px] text-white/55 leading-relaxed">
                                Lee la tabla <code className="text-emerald-300">sys300</code> con los <strong>nombres comerciales</strong>, RUC y datos de cada empresa.
                            </div>
                        </div>
                    </div>
                </div>

                {/* Espaciador físico compacto */}
                <div className="h-6" />

                {/* ── Panel de bases descubiertas ──────────────────────── */}
                <AnimatePresence>
                    {discoveredDatabases.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="border-t border-white/[0.04] pt-8 mb-32"
                        >
                            {/* Selector buscable: reemplaza la cuadrícula de 22 botones.
                                Con esa cantidad de empresas, barrer la pantalla con la vista
                                era más lento que escribir tres letras. */}
                            <div className="w-full px-10 pb-16">
                                <div className="mx-auto w-full max-w-2xl">
                                    <div className="mb-3 flex items-center justify-between">
                                        <span className="text-[12px] font-bold uppercase tracking-[0.2em] text-white/30">
                                            Bases detectadas
                                        </span>
                                        <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[12px] font-bold text-cyan-400">
                                            {discoveredDatabases.length}
                                        </span>
                                    </div>

                                    <CompanySelector
                                        companies={companyRows}
                                        activeDb={connInfo.database}
                                        switchingDb={switchingDatabase}
                                        onSelect={onSelectDatabase}
                                        disabled={Boolean(switchingDatabase)}
                                    />
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
