/**
 * Archivo: Login.jsx
 * Rol: pantalla inicial de autenticacion y preconexion.
 * Recibe desde: App.jsx cuando no existe sesion activa.
 * Se conecta con: handleAuthLogin y handleConnect definidos en App.jsx.
 * Responsabilidades: capturar credenciales, mostrar estados y abrir acceso manual.
 **/

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    AlertCircle, Database, Eye, EyeOff, Globe, Loader2, Lock, Settings, Users, X
} from 'lucide-react';
import { apiPost } from '../services/api';

export function LoginView({
    isConnected,
    loading,
    authPending,
    isVerifying,
    isRestoringSession,
    showAdvanced,
    showDevOptions,
    error,
    errorDeSistema = false,
    tempCreds,
    setTempCreds,
    showPassword,
    setShowPassword,
    handleAuthLogin,
    handleConnect,
    cancelSessionRestore,
    setIsVerifying,
    setError,
    setShowAdvanced,
    handleTitleClick,
    maskedHost,
    showHost,
    setShowHost,
    connInfo,
    setConnInfo
}) {
    const [forgotOpen, setForgotOpen] = useState(false);

    return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-[#020617] relative overflow-hidden">
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#FF6900]/10 blur-[120px] rounded-full" />
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#002E45]/30 blur-[120px] rounded-full" />
            <motion.div
                initial={false}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-panel pb-4 sm:pb-6 px-5 sm:px-8 rounded-[32px] sm:rounded-[44px] w-full max-w-[28rem] border border-white/10 shadow-[0_0_120px_rgba(0,0,0,0.7)] relative z-10 bg-[#0a1622]/80 backdrop-blur-3xl overflow-hidden"
            >
                <div className="flex flex-col items-center pt-3 text-center max-h-[calc(100vh-3rem)] overflow-y-auto custom-scrollbar">
                    {/* Logo VicMar Data AI */}
                    <div className="relative w-full max-w-[150px] h-auto aspect-video mb-1 sm:mb-2 group flex items-center justify-center">
                        <img
                            src="/logo.png"
                            alt="VicMar Data AI Logo"
                            className="w-full h-full object-contain relative z-10 scale-[1] sm:scale-[1]"
                            style={{
                                filter: 'drop-shadow(0 0 35px rgba(255, 105, 0, 0.35))'
                            }}
                        />
                        <div className="absolute inset-0 bg-[#FF6900]/5 blur-[60px] sm:blur-[100px] rounded-full animate-pulse z-0 pointer-events-none" />
                    </div>
                    <h1
                        onClick={handleTitleClick}
                        className="text-2xl sm:text-3xl font-black tracking-[-0.08em] text-white mb-1 font-vanguard drop-shadow-[0_0_20px_rgba(255,255,255,0.1)] cursor-default select-none transition-all active:scale-95"
                    >
                        <span>VicMar</span>
                        <span className="ml-2">Data AI</span>
                    </h1>
                    <p
                        onClick={() => {
                            // Mostrar el host solo cuando ya estamos conectados (dashboard)
                            if (isConnected) setShowHost(prev => !prev);
                        }}
                        className="text-[11px] sm:text-[13px] font-black tracking-tight uppercase leading-relaxed mb-2 sm:mb-3 font-tech cursor-pointer active:scale-95 transition-all select-none"
                        style={{
                            color: "#FF6900",
                            textShadow: "0 0 4px rgba(255,105,0,0.35)"
                        }}
                    >
                        INTELIGENCIA DE NEGOCIOS
                    </p>

                    <div className="w-full space-y-3">
                        {/* Seccion: alterna restauracion, loading, login o panel avanzado. */}
                        {isRestoringSession ? (
                            <div className="py-20 flex flex-col items-center justify-center space-y-6">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-orange-500/20 blur-xl rounded-full animate-pulse" />
                                    <Loader2 className="w-12 h-12 text-orange-500 animate-spin relative z-10" />
                                </div>
                                <div className="text-center space-y-2">
                                    <p className="text-white font-black uppercase tracking-[0.4em] text-xs">Restaurando sesion</p>
                                    <p className="text-white/30 text-[12px] uppercase tracking-[0.3em]">Reconectando tu ecosistema de datos...</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => cancelSessionRestore?.()}
                                    className="px-6 py-3 rounded-full border border-orange-500/30 text-orange-300 text-[12px] font-black uppercase tracking-[0.35em] hover:bg-orange-500/10 transition-all"
                                >
                                    Continuar manualmente
                                </button>
                            </div>
                        ) : loading ? (
                            <div className="py-20 flex flex-col items-center justify-center space-y-6">
                                <div className="relative">
                                    <div className="absolute inset-0 bg-orange-500/20 blur-xl rounded-full animate-pulse" />
                                    <Loader2 className="w-12 h-12 text-orange-500 animate-spin relative z-10" />
                                </div>
                                <div className="text-center space-y-2">
                                    <p className="text-white font-black uppercase tracking-[0.4em] text-xs">Sincronizando Autoridad</p>
                                    <p className="text-white/20 text-[11px] uppercase tracking-widest animate-pulse">Inyectando ADN Maestro...</p>
                                </div>
                            </div>
                        ) : (
                            <motion.div
                                // `initial={false}` — igual que el panel que lo contiene (arriba).
                                //
                                // Con `initial={{opacity:0}}` (como estaba hasta el 31/08/2026) el
                                // marco de la tarjeta se pintaba completo desde el primer frame
                                // —borde, fondo y su sombra de 120px— mientras el formulario
                                // arrancaba invisible y se desvanecía hacia adentro. En esa
                                // fracción de segundo se veía la tarjeta a medio llenar: eso es
                                // la "sombra"/silueta que el usuario seguía reportando incluso
                                // después de quitar el placeholder estático de index.html.
                                // Sin animación de entrada, la tarjeta y su contenido aparecen
                                // como una sola pieza.
                                initial={false} animate={{ opacity: 1, scale: 1 }}
                                className="w-full space-y-4 pt-0"
                            >
                                <div className="text-center space-y-2 mb-4">
                                    <h2 className="text-white text-lg font-bold tracking-[-0.02em] uppercase font-vanguard">
                                        Acceso al Sistema
                                    </h2>
                                    <div className="flex items-center justify-center gap-2">
                                        <div className="w-6 h-px bg-gradient-to-r from-orange-500 to-transparent" />
                                        <div className="w-1.5 h-1.5 rounded-full bg-orange-400/80" style={{boxShadow: '0 0 10px rgba(255,105,0,0.5)'}} />
                                        <div className="w-6 h-px bg-gradient-to-l from-orange-500 to-transparent" />
                                    </div>
                                </div>

                                <form onSubmit={handleAuthLogin} className="space-y-3">
                                    {/* Seccion: captura de usuario. */}
                                    <div className="group">
                                        <label className="block text-white/50 text-[10px] font-semibold uppercase tracking-wider mb-1 ml-1">Usuario</label>
                                        <div className="flex items-center bg-white/[0.04] border border-white/12 rounded-[32px] focus-within:border-orange-500/50 focus-within:bg-white/[0.06] transition-all duration-200 overflow-hidden">
                                            <div className="shrink-0 px-4 py-2.5 flex items-center justify-center">
                                                <Users className="text-white/35 group-focus-within:text-orange-400 transition-colors" size={18} />
                                            </div>
                                            <input
                                                autoFocus
                                                type="text"
                                                placeholder="Ingresa tu usuario"
                                                aria-label="Usuario"
                                                autoComplete="username"
                                                value={tempCreds.username}
                                                onChange={(e) => setTempCreds(prev => ({ ...prev, username: e.target.value }))}
                                                className="flex-1 min-w-0 bg-transparent outline-none text-white text-sm px-4 py-2.5 font-medium placeholder:text-white/20"
                                            />
                                        </div>
                                    </div>

                                    {/* Seccion: captura de contrasena. */}
                                    <div className="group relative">
                                        <label className="block text-white/50 text-[10px] font-semibold uppercase tracking-wider mb-1 ml-1">Contraseña</label>
                                        <div className="flex items-center bg-white/[0.04] border border-white/12 rounded-[32px] focus-within:border-orange-500/50 focus-within:bg-white/[0.06] transition-all duration-200 overflow-hidden">
                                            <div className="shrink-0 px-4 py-2.5 flex items-center justify-center">
                                                <Lock className="text-white/35 group-focus-within:text-orange-400 transition-colors" size={18} />
                                            </div>
                                            <input
                                                type={showPassword ? "text" : "password"}
                                                placeholder="Ingresa tu contraseña"
                                                aria-label="Contraseña"
                                                autoComplete="current-password"
                                                value={tempCreds.password}
                                                onChange={(e) => setTempCreds(prev => ({ ...prev, password: e.target.value }))}
                                                className="flex-1 min-w-0 bg-transparent outline-none text-white text-sm px-4 pr-28 py-2.5 font-medium placeholder:text-white/20"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowPassword(!showPassword)}
                                                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                                aria-pressed={showPassword}
                                                className="absolute right-5 top-1/2 -translate-y-1/2 text-emerald-400/70 hover:text-emerald-300 text-xs font-semibold tracking-wide transition-colors"
                                            >
                                                {showPassword ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                                            </button>
                                        </div>
                                    </div>

                                    <div className="flex justify-end pt-0">
                                        <button
                                            type="button"
                                            onClick={() => setForgotOpen(true)}
                                            className="text-[11px] font-semibold text-orange-400/60 hover:text-orange-300 tracking-wide transition-colors"
                                        >
                                            ¿Olvidaste tu contraseña?
                                        </button>
                                    </div>

                                    {error && !errorDeSistema && (
                                        <motion.div role="alert" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-3 bg-red-500/10 border border-red-500/25 rounded-xl text-red-300 text-xs text-center font-semibold border-l-4 border-red-500 shadow-lg">
                                            {error}
                                        </motion.div>
                                    )}

                                    <div className="pt-3 flex flex-col gap-3">
                                        <button
                                            type="submit"
                                            disabled={authPending || !tempCreds.username || !tempCreds.password}
                                            className="w-full py-3 rounded-[28px] text-white font-bold uppercase text-[13px] tracking-[0.08em] transition-all duration-200 flex items-center justify-center gap-1.5 relative overflow-hidden group/btn cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                                            style={{
                                                background: authPending || !tempCreds.username || !tempCreds.password
                                                    ? 'rgba(255,105,0,0.4)'
                                                    : 'linear-gradient(135deg, #FF6900 0%, #ea7d06 50%, #002E45 100%)',
                                                boxShadow: authPending || !tempCreds.username || !tempCreds.password
                                                    ? 'none'
                                                    : '0 8px 20px rgba(255,105,0,0.3), inset 0 1px 0 rgba(255,255,255,0.15)',
                                            }}
                                            onMouseEnter={(e) => {
                                                if (!authPending && tempCreds.username && tempCreds.password) {
                                                    e.currentTarget.style.boxShadow = '0 12px 28px rgba(255,105,0,0.45), inset 0 1px 0 rgba(255,255,255,0.2)';
                                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (!authPending && tempCreds.username && tempCreds.password) {
                                                    e.currentTarget.style.boxShadow = '0 8px 20px rgba(255,105,0,0.3), inset 0 1px 0 rgba(255,255,255,0.15)';
                                                    e.currentTarget.style.transform = 'translateY(0)';
                                                }
                                            }}
                                        >
                                            {authPending ? (
                                                <Loader2 size={18} className="animate-spin" />
                                            ) : (
                                                <>
                                                    <span>✓</span>
                                                    <span>Ingresar al Sistema</span>
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </form>

                                {showDevOptions && (
                                    <div className="pt-4 border-t border-white/10">
                                        <button
                                            onClick={() => setShowAdvanced(true)}
                                            className="w-full py-3 rounded-[30px] bg-white/5 border border-white/10 text-white/50 font-bold uppercase tracking-[0.3em] text-[11px] hover:bg-white/10 hover:text-orange-400 hover:border-orange-500/30 transition-all flex items-center justify-center gap-3 group"
                                        >
                                            <Settings size={16} className="group-hover:rotate-90 transition-transform duration-1000" />
                                            <span>Ajustes de Infraestructura</span>
                                        </button>
                                    </div>
                                )}

                                {showAdvanced && (
                                    <motion.form
                                        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                        onSubmit={handleConnect} className="space-y-5 w-full text-left mt-6 pt-6 border-t border-white/10"
                                    >
                                        <div className="flex items-center justify-between mb-6">
                                            <div className="flex flex-col">
                                                <h2 className="text-[12px] font-black text-white uppercase tracking-[0.4em]">Estacion de Enlace</h2>
                                                <span className="text-[11px] text-orange-500/50 font-bold uppercase tracking-widest mt-1">Configuracion del Nodo Maestro</span>
                                            </div>
                                            <button type="button" onClick={() => setShowAdvanced(false)} className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-full text-[11px] text-white/40 hover:text-white uppercase font-black tracking-widest transition-all">Volver</button>
                                        </div>
                                        <div className="space-y-4">
                                            <div className="space-y-2 relative">
                                                <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2 flex items-center gap-2">
                                                    <Globe size={10} className="text-orange-500" /> Puerta de Enlace (Host)
                                                </label>
                                                <div className="relative">
                                                    <input
                                                        type="text"
                                                        className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner placeholder:text-white/5"
                                                        placeholder="ENDPOINT"
                                                        value={maskedHost}
                                                        readOnly={!showHost}
                                                        onChange={(e) => showHost && setConnInfo({ ...connInfo, host: e.target.value })}
                                                    />
                                                    <button
                                                        type="button"
                                                        onClick={() => setShowHost(prev => !prev)}
                                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
                                                        title={showHost ? "Ocultar host" : "Mostrar host"}
                                                    >
                                                        {showHost ? <EyeOff size={18} /> : <Eye size={18} />}
                                                    </button>
                                                </div>
                                                {!showHost && (
                                                    <p className="text-[11px] text-white/30 mt-1">El host esta oculto por seguridad. Pulsa el icono para verlo.</p>
                                                )}
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2 flex items-center gap-2">
                                                    <Settings size={10} className="text-orange-500" /> Modo de Autenticacion
                                                </label>
                                                <select
                                                    className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner"
                                                    value={connInfo.auth_type || ''}
                                                    onChange={(e) => setConnInfo({ ...connInfo, auth_type: e.target.value })}
                                                >
                                                    <option value="">Automatico</option>
                                                    <option value="Windows Authentication">Windows Authentication</option>
                                                    <option value="SQL Server Authentication">SQL Server Authentication</option>
                                                </select>
                                                <p className="text-[11px] text-white/30 mt-1">
                                                    Automatico usa Windows si no defines credenciales SQL.
                                                </p>
                                            </div>
                                            {connInfo.auth_type !== 'Windows Authentication' && (
                                                <>
                                                    <div className="space-y-2">
                                                        <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2">
                                                            Usuario SQL
                                                        </label>
                                                        <input
                                                            type="text"
                                                            className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner placeholder:text-white/5"
                                                            placeholder="sa"
                                                            value={connInfo.user || ''}
                                                            onChange={(e) => setConnInfo({ ...connInfo, user: e.target.value })}
                                                        />
                                                    </div>
                                                    <div className="space-y-2">
                                                        <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2">
                                                            Contrasena SQL
                                                        </label>
                                                        <input
                                                            type="password"
                                                            className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner placeholder:text-white/5"
                                                            placeholder="••••••••"
                                                            value={connInfo.password || ''}
                                                            onChange={(e) => setConnInfo({ ...connInfo, password: e.target.value })}
                                                        />
                                                    </div>
                                                </>
                                            )}
                                            <div className="space-y-2">
                                                <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2">
                                                    Driver ODBC
                                                </label>
                                                <input
                                                    type="text"
                                                    className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner placeholder:text-white/5"
                                                    placeholder="ODBC Driver 17 for SQL Server"
                                                    value={connInfo.driver || ''}
                                                    onChange={(e) => setConnInfo({ ...connInfo, driver: e.target.value })}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <label className="text-[11px] font-black text-white/30 uppercase tracking-[0.3em] ml-2 flex items-center gap-2">
                                                    <Database size={10} className="text-orange-500" /> Ecosistema de Datos (DB)
                                                </label>
                                                <input type="text" className="w-full bg-black/40 border border-white/10 outline-none focus:border-orange-500/50 text-white text-sm px-6 py-4 rounded-[20px] font-tech tracking-widest transition-all shadow-inner placeholder:text-white/5" placeholder="STACK" value={connInfo.database} onChange={(e) => setConnInfo({ ...connInfo, database: e.target.value })} />
                                            </div>
                                        </div>
                                        <div className="pt-6">
                                            <button type="submit" disabled={loading} className="w-full py-4 rounded-[30px] bg-gradient-to-r from-orange-600 to-[#002E45] text-white text-[14px] font-black uppercase tracking-[0.25em] shadow-[0_20px_40px_rgba(255,105,0,0.3)] hover:shadow-orange-500/50 transition-all active:scale-[0.98]">
                                                {loading ? 'Sincronizando...' : 'Conectar'}
                                            </button>
                                        </div>
                                    </motion.form>
                                )}
                            </motion.div>
                        )}
                    </div>
                    {/* Panel de "algo va mal en el sistema". Va condicionado a
                        `errorDeSistema` (31/08/2026): antes salía con CUALQUIER
                        error, así que al escribir mal la contraseña el mismo
                        texto aparecía dos veces —la franja roja de arriba, que
                        es la que corresponde, y otra vez aquí en azul— con un
                        botón "Refrescar Sistema" que no arregla unas
                        credenciales equivocadas. Ahora solo aparece cuando
                        recargar puede servir de algo: el servidor no responde o
                        la conexión SQL se cayó. */}
                    {error && errorDeSistema && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 p-4 rounded-2xl bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[12px] flex flex-col items-center gap-3 font-bold uppercase tracking-wider text-center">
                            <div className="flex items-center gap-2"><AlertCircle size={16} /> {error}</div>
                            <button type="button" onClick={() => window.location.reload()} className="px-4 py-2 bg-orange-500 text-white rounded-full text-[11px] hover:bg-orange-400 transition-colors">Refrescar Sistema</button>
                        </motion.div>
                    )}
                </div>
            </motion.div>

            <ForgotPasswordModal
                open={forgotOpen}
                onClose={() => setForgotOpen(false)}
                initialUsername={tempCreds?.username}
            />
        </div>
    );
}

// "Olvidé mi contraseña" (Fase 5 — 28/08/2026): flujo de
// 2 pasos con código de un solo uso enviado por correo (backend/core/
// email_service.py + core/password_reset.py). Autocontenido: no depende de
// ningún estado de App.jsx aparte del username ya tecleado en el login.
function ForgotPasswordModal({ open, onClose, initialUsername }) {
    // El identificador de esta app es un usuario corto (ej. "admin"), nunca
    // el correo — pero es un error natural escribir el correo en el login
    // pensando que es el usuario. Si lo que trae `initialUsername` parece un
    // correo, precargarlo aquí solo repetiría ese mismo error, así que se
    // descarta y se deja el campo vacío (reportado 29/08/2026).
    const usernameValido = (v) => (v && !v.includes('@') ? v : '');
    const [step, setStep] = useState('request'); // 'request' | 'confirm' | 'done'
    const [username, setUsername] = useState(usernameValido(initialUsername));
    const [code, setCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPwd, setShowPwd] = useState(false);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState('');
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        if (!open) return;
        setStep('request');
        setUsername(usernameValido(initialUsername));
        setCode('');
        setNewPassword('');
        setConfirmPassword('');
        setMessage('');
        setErrorMsg('');
    }, [open, initialUsername]);

    if (!open) return null;

    const solicitarCodigo = async (e) => {
        e.preventDefault();
        if (!username.trim() || loading) return;
        setLoading(true);
        setErrorMsg('');
        const generico = 'Si el usuario existe y tiene un correo registrado, te enviamos un código de verificación.';
        try {
            const res = await apiPost('/password-reset/request', { username: username.trim() });
            setMessage(res.data?.message || generico);
        } catch (_err) {
            // Mismo mensaje ante error de red: no se revela si el usuario existe.
            setMessage(generico);
        } finally {
            setLoading(false);
            setStep('confirm');
        }
    };

    const confirmarNuevaPassword = async (e) => {
        e.preventDefault();
        if (loading) return;
        setErrorMsg('');
        if (newPassword.length < 8) { setErrorMsg('La nueva contraseña debe tener mínimo 8 caracteres.'); return; }
        if (newPassword !== confirmPassword) { setErrorMsg('Las contraseñas no coinciden.'); return; }
        setLoading(true);
        try {
            await apiPost('/password-reset/confirm', {
                username: username.trim(),
                code: code.trim(),
                new_password: newPassword,
            });
            setStep('done');
        } catch (err) {
            setErrorMsg(err?.response?.data?.detail || 'No se pudo restablecer la contraseña.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label="Recuperar contraseña">
            <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                className="w-full max-w-sm rounded-[28px] border border-white/10 bg-[#0f172a] p-8 shadow-2xl"
            >
                <div className="mb-6 flex items-center justify-between gap-3">
                    <h3 className="text-lg font-black uppercase text-white">Recuperar acceso</h3>
                    <button type="button" onClick={onClose} aria-label="Cerrar" className="shrink-0 text-white/40 hover:text-white">
                        <X size={18} aria-hidden="true" />
                    </button>
                </div>

                {step === 'request' && (
                    <form onSubmit={solicitarCodigo} className="space-y-4">
                        <p className="text-[13px] text-white/50">
                            Ingresa tu <strong className="text-white/70">nombre de usuario</strong> (no tu
                            correo). Si ese usuario tiene un correo guardado en Mi Perfil, te enviaremos
                            ahí un código para restablecer tu contraseña.
                        </p>
                        <input
                            type="text"
                            autoFocus
                            placeholder="Nombre de usuario (ej. admin)"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-3.5 text-white outline-none focus:border-orange-500/50"
                        />
                        <button
                            type="submit"
                            disabled={loading || !username.trim()}
                            className="w-full rounded-2xl bg-orange-600 px-5 py-3.5 text-[13px] font-black uppercase tracking-widest text-white transition-all hover:bg-orange-500 disabled:opacity-40"
                        >
                            {loading ? 'Enviando…' : 'Enviar código'}
                        </button>
                    </form>
                )}

                {step === 'confirm' && (
                    <form onSubmit={confirmarNuevaPassword} className="space-y-4">
                        {message && (
                            <p className="safe-text-box rounded-xl border border-orange-500/20 bg-orange-500/10 text-[12px] leading-relaxed text-orange-200">
                                {message}
                            </p>
                        )}
                        <input
                            type="text"
                            inputMode="numeric"
                            maxLength={6}
                            autoFocus
                            placeholder="Código de 6 dígitos"
                            value={code}
                            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-3.5 text-center text-lg tracking-[0.4em] text-white outline-none focus:border-orange-500/50"
                        />
                        <div className="relative">
                            <input
                                type={showPwd ? 'text' : 'password'}
                                placeholder="Nueva contraseña"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-3.5 pr-12 text-white outline-none focus:border-orange-500/50"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPwd((v) => !v)}
                                aria-label={showPwd ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                            >
                                {showPwd ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
                            </button>
                        </div>
                        <input
                            type={showPwd ? 'text' : 'password'}
                            placeholder="Repite la nueva contraseña"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full rounded-2xl border border-white/10 bg-black/40 px-5 py-3.5 text-white outline-none focus:border-orange-500/50"
                        />
                        {errorMsg && <p className="text-[12px] text-rose-400">{errorMsg}</p>}
                        <button
                            type="submit"
                            disabled={loading || !code || !newPassword || !confirmPassword}
                            className="w-full rounded-2xl bg-orange-600 px-5 py-3.5 text-[13px] font-black uppercase tracking-widest text-white transition-all hover:bg-orange-500 disabled:opacity-40"
                        >
                            {loading ? 'Guardando…' : 'Restablecer contraseña'}
                        </button>
                        <button
                            type="button"
                            onClick={() => setStep('request')}
                            className="w-full text-center text-[12px] font-bold uppercase tracking-widest text-white/40 hover:text-white/70"
                        >
                            Reenviar código
                        </button>
                    </form>
                )}

                {step === 'done' && (
                    <div className="space-y-4 text-center">
                        <p className="text-[14px] text-emerald-300">Contraseña actualizada. Ya puedes iniciar sesión.</p>
                        <button
                            type="button"
                            onClick={onClose}
                            className="w-full rounded-2xl bg-orange-600 px-5 py-3.5 text-[13px] font-black uppercase tracking-widest text-white hover:bg-orange-500"
                        >
                            Volver al login
                        </button>
                    </div>
                )}
            </motion.div>
        </div>
    );
}




