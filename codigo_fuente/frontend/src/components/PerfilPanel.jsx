import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
    Camera, Trash2, X, Eye, EyeOff, KeyRound, ShieldCheck, Lock, Clock,
    Save, Mail, Pencil,
} from 'lucide-react';
import { apiGet, apiPost, apiPut, apiDelete } from '../services/api';

// Panel "Mi Perfil" — abre como un cajón a la derecha sobre el dashboard
// actual (no navega a otra pantalla ni abre otra pestaña), siguiendo el
// mismo patrón del proyecto hermano TripleA_VentasIA.
// Por eso no lleva selector de empresa: el botón de cierre es "Volver", no
// "Cambiar base" — cerrar el panel ya te deja donde estabas.

const MAX_AVATAR_DIM = 256;

function resizeImageToDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('No se pudo leer el archivo.'));
        reader.onload = () => {
            const img = new Image();
            img.onerror = () => reject(new Error('El archivo no es una imagen válida.'));
            img.onload = () => {
                const size = Math.min(img.width, img.height);
                const sx = (img.width - size) / 2;
                const sy = (img.height - size) / 2;
                const target = Math.min(MAX_AVATAR_DIM, size);
                const canvas = document.createElement('canvas');
                canvas.width = target;
                canvas.height = target;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, sx, sy, size, size, 0, 0, target, target);
                resolve(canvas.toDataURL('image/jpeg', 0.85));
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });
}

export function PerfilPanel({ open, onClose, userAuth, avatarUrl, onAvatarChange }) {
    const [profile, setProfile] = useState(null);
    const [toast, setToast] = useState('');
    const fileInputRef = useRef(null);
    const [pendingPhoto, setPendingPhoto] = useState(null);
    const [savingPhoto, setSavingPhoto] = useState(false);
    const [deletingPhoto, setDeletingPhoto] = useState(false);

    const [emailEditing, setEmailEditing] = useState(false);
    const [emailDraft, setEmailDraft] = useState('');
    const [savingEmail, setSavingEmail] = useState(false);
    const [emailError, setEmailError] = useState('');

    const [pwdCurrent, setPwdCurrent] = useState('');
    const [pwdNew, setPwdNew] = useState('');
    const [pwdConfirm, setPwdConfirm] = useState('');
    const [showPwdCurrent, setShowPwdCurrent] = useState(false);
    const [showPwdNew, setShowPwdNew] = useState(false);
    const [showPwdConfirm, setShowPwdConfirm] = useState(false);
    const [pwdError, setPwdError] = useState('');
    const [pwdSaving, setPwdSaving] = useState(false);

    useEffect(() => {
        if (!open) return undefined;
        let cancelled = false;
        apiGet('/profile')
            .then((res) => { if (!cancelled) setProfile(res.data?.profile || null); })
            .catch(() => { if (!cancelled) setProfile(null); });
        return () => { cancelled = true; };
    }, [open]);

    useEffect(() => {
        if (open) return;
        // Al cerrar, se limpia todo lo que no debe sobrevivir a la próxima
        // apertura — sobre todo las contraseñas en memoria.
        setPendingPhoto(null);
        setPwdCurrent(''); setPwdNew(''); setPwdConfirm(''); setPwdError('');
        setEmailEditing(false); setEmailError('');
        setToast('');
    }, [open]);

    useEffect(() => {
        if (!open) return undefined;
        const onKey = (e) => { if (e.key === 'Escape') onClose(); };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [open, onClose]);

    const handleSelectFile = async (e) => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            setToast('Selecciona un archivo de imagen (PNG, JPG o WEBP).');
            return;
        }
        try {
            const dataUrl = await resizeImageToDataUrl(file);
            setPendingPhoto(dataUrl);
        } catch (_err) {
            setToast('No se pudo procesar esa imagen. Intenta con otra.');
        }
    };

    const guardarFoto = async () => {
        if (!pendingPhoto || savingPhoto) return;
        setSavingPhoto(true);
        try {
            await apiPost('/profile/avatar', { image_data_url: pendingPhoto });
            setProfile((p) => (p ? { ...p, avatar: pendingPhoto } : p));
            onAvatarChange?.(pendingPhoto);
            setPendingPhoto(null);
            setToast('Foto de perfil actualizada correctamente.');
        } catch (err) {
            setToast(err?.response?.data?.detail || 'No se pudo guardar la foto.');
        } finally {
            setSavingPhoto(false);
        }
    };

    const eliminarFoto = async () => {
        if (deletingPhoto) return;
        setDeletingPhoto(true);
        try {
            await apiDelete('/profile/avatar');
            setProfile((p) => (p ? { ...p, avatar: null } : p));
            onAvatarChange?.(null);
            setToast('Foto de perfil eliminada.');
        } catch (_err) {
            setToast('No se pudo eliminar la foto.');
        } finally {
            setDeletingPhoto(false);
        }
    };

    const iniciarEdicionCorreo = () => {
        setEmailDraft(profile?.email || '');
        setEmailError('');
        setEmailEditing(true);
    };

    const guardarCorreo = async () => {
        setSavingEmail(true);
        setEmailError('');
        try {
            const res = await apiPut('/profile/email', { email: emailDraft.trim() });
            setProfile((p) => (p ? { ...p, email: res.data?.email ?? emailDraft.trim() } : p));
            setEmailEditing(false);
        } catch (err) {
            setEmailError(err?.response?.data?.detail || 'No se pudo guardar el correo.');
        } finally {
            setSavingEmail(false);
        }
    };

    const cambiarPassword = async () => {
        setPwdError('');
        if (pwdNew.length < 8) { setPwdError('La nueva contraseña debe tener mínimo 8 caracteres.'); return; }
        if (pwdNew !== pwdConfirm) { setPwdError('Las contraseñas nuevas no coinciden.'); return; }
        setPwdSaving(true);
        try {
            await apiPost('/profile/password', { current_password: pwdCurrent, new_password: pwdNew });
            setPwdCurrent(''); setPwdNew(''); setPwdConfirm('');
            setToast('Contraseña actualizada correctamente.');
        } catch (err) {
            setPwdError(err?.response?.data?.detail || 'No se pudo cambiar la contraseña.');
        } finally {
            setPwdSaving(false);
        }
    };

    const nombre = profile?.name || userAuth?.name || 'Usuario';
    const iniciales = nombre.split(' ').filter(Boolean).map((p) => p[0]).join('').slice(0, 2).toUpperCase();
    const fotoActual = pendingPhoto || profile?.avatar || avatarUrl || null;

    return (
        <AnimatePresence>
            {open && (
                <React.Fragment>
                    <motion.div
                        key="perfil-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[90] bg-black/60"
                        onClick={onClose}
                    />
                    <motion.aside
                        key="perfil-panel"
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'tween', duration: 0.25, ease: 'easeOut' }}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Mi perfil"
                        className="custom-scrollbar fixed right-0 top-0 z-[91] flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-white/10 bg-[#0B0F14]"
                    >
                        <div className="flex items-center justify-between border-b border-white/10 px-6 py-5">
                            <h2 className="text-lg font-black uppercase italic tracking-tight text-white">Mi Perfil</h2>
                            <button
                                type="button"
                                onClick={onClose}
                                aria-label="Volver"
                                title="Volver"
                                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-white/60 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
                            >
                                <X size={14} aria-hidden="true" /> Volver
                            </button>
                        </div>

                        {toast && (
                            <div className="mx-6 mt-4 flex items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-[13px] font-medium text-emerald-300">
                                <span>{toast}</span>
                                <button type="button" onClick={() => setToast('')} aria-label="Cerrar aviso" className="text-emerald-300/70 hover:text-emerald-200">
                                    <X size={14} aria-hidden="true" />
                                </button>
                            </div>
                        )}

                        <div className="flex flex-col gap-5 p-6">
                            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                                <div className="group relative mx-auto h-28 w-28">
                                    <div className="h-28 w-28 overflow-hidden rounded-full border-2 border-cyan-500/40 bg-cyan-500/10">
                                        {fotoActual ? (
                                            <img src={fotoActual} alt="Foto de perfil" className="h-full w-full object-cover" />
                                        ) : (
                                            <div className="flex h-full w-full items-center justify-center text-2xl font-black text-cyan-300">
                                                {iniciales || 'U'}
                                            </div>
                                        )}
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        title="Cambiar foto"
                                        aria-label="Cambiar foto de perfil"
                                        className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100 focus:outline-none"
                                    >
                                        <Camera size={20} aria-hidden="true" />
                                    </button>
                                    {fotoActual && !pendingPhoto && (
                                        <button
                                            type="button"
                                            onClick={eliminarFoto}
                                            disabled={deletingPhoto}
                                            title="Eliminar foto"
                                            aria-label="Eliminar foto de perfil"
                                            className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border-2 border-[#0B0F14] bg-rose-500 text-white shadow-lg transition-transform hover:scale-105 disabled:opacity-50"
                                        >
                                            <Trash2 size={13} aria-hidden="true" />
                                        </button>
                                    )}
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/png,image/jpeg,image/webp"
                                    className="hidden"
                                    onChange={handleSelectFile}
                                />
                                <div className="mt-3 text-center">
                                    <p className="text-base font-bold text-white">{nombre}</p>
                                    <p className="text-[12px] uppercase tracking-wide text-white/40">@{profile?.username || userAuth?.username || '—'}</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-white/70 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
                                >
                                    <Camera size={14} aria-hidden="true" /> Cambiar foto de perfil
                                </button>

                                {pendingPhoto && (
                                    <div className="mt-4 rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4">
                                        <p className="mb-3 text-[12px] font-medium text-white/70">
                                            Seleccionaste una nueva foto. Puedes guardarla sin cambiar tu contraseña.
                                        </p>
                                        <div className="flex gap-2">
                                            <button
                                                type="button"
                                                onClick={guardarFoto}
                                                disabled={savingPhoto}
                                                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-rose-500 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-white transition-colors hover:bg-rose-400 disabled:opacity-50"
                                            >
                                                <Save size={13} aria-hidden="true" /> {savingPhoto ? 'Guardando…' : 'Guardar foto'}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setPendingPhoto(null)}
                                                disabled={savingPhoto}
                                                className="rounded-lg border border-white/10 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-white/60 hover:text-white"
                                            >
                                                Cancelar
                                            </button>
                                        </div>
                                    </div>
                                )}

                                <div className="mt-4 space-y-3 border-t border-white/10 pt-4 text-[13px]">
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="flex items-center gap-2 text-white/40"><Mail size={13} aria-hidden="true" /> Correo</span>
                                        {!emailEditing && (
                                            <button type="button" onClick={iniciarEdicionCorreo} className="flex items-center gap-1.5 text-white/80 hover:text-cyan-300">
                                                {profile?.email || 'Agregar correo'} <Pencil size={11} className="text-white/30" aria-hidden="true" />
                                            </button>
                                        )}
                                    </div>
                                    {emailEditing && (
                                        <div className="flex flex-col gap-2">
                                            <input
                                                type="email"
                                                value={emailDraft}
                                                onChange={(e) => setEmailDraft(e.target.value)}
                                                placeholder="tucorreo@gmail.com"
                                                className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[13px] text-white outline-none focus:border-cyan-500/40"
                                            />
                                            {emailError && <p className="text-[12px] text-rose-400">{emailError}</p>}
                                            <div className="flex gap-2">
                                                <button type="button" onClick={guardarCorreo} disabled={savingEmail} className="flex-1 rounded-lg bg-cyan-500/20 px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-cyan-300 hover:bg-cyan-500/30 disabled:opacity-50">
                                                    {savingEmail ? 'Guardando…' : 'Guardar'}
                                                </button>
                                                <button type="button" onClick={() => setEmailEditing(false)} className="rounded-lg border border-white/10 px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-white/60 hover:text-white">
                                                    Cancelar
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                    <div className="flex items-center justify-between text-white/40">
                                        <span>Registrado</span>
                                        <span className="text-white/70">
                                            {profile?.created_at
                                                ? new Date(profile.created_at).toLocaleDateString('es-EC', { day: '2-digit', month: 'long', year: 'numeric' })
                                                : '—'}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between text-white/40">
                                        <span>Último acceso</span>
                                        <span className="text-white/70">
                                            {profile?.last_login
                                                ? new Date(profile.last_login).toLocaleString('es-EC', { dateStyle: 'short', timeStyle: 'short' })
                                                : '—'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                                <h3 className="mb-4 flex items-center gap-2 text-[13px] font-bold uppercase tracking-wide text-amber-300">
                                    <KeyRound size={15} aria-hidden="true" /> Cambiar Contraseña
                                </h3>
                                <div className="flex flex-col gap-3">
                                    <PasswordField label="Contraseña actual" value={pwdCurrent} onChange={setPwdCurrent} show={showPwdCurrent} onToggleShow={() => setShowPwdCurrent((v) => !v)} placeholder="Tu contraseña actual" />
                                    <PasswordField label="Nueva contraseña" value={pwdNew} onChange={setPwdNew} show={showPwdNew} onToggleShow={() => setShowPwdNew((v) => !v)} placeholder="Mínimo 8 caracteres" />
                                    <PasswordField label="Confirmar nueva contraseña" value={pwdConfirm} onChange={setPwdConfirm} show={showPwdConfirm} onToggleShow={() => setShowPwdConfirm((v) => !v)} placeholder="Repite la nueva contraseña" />
                                    {pwdError && <p className="text-[12px] text-rose-400">{pwdError}</p>}
                                    <div className="flex gap-2 pt-1">
                                        <button
                                            type="button"
                                            onClick={cambiarPassword}
                                            disabled={pwdSaving || !pwdCurrent || !pwdNew || !pwdConfirm}
                                            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-black transition-colors hover:bg-amber-400 disabled:opacity-40"
                                        >
                                            <Save size={13} aria-hidden="true" /> {pwdSaving ? 'Guardando…' : 'Cambiar Contraseña'}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => { setPwdCurrent(''); setPwdNew(''); setPwdConfirm(''); setPwdError(''); }}
                                            className="rounded-lg border border-white/10 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-white/60 hover:text-white"
                                        >
                                            Cancelar
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                                <h3 className="mb-4 flex items-center gap-2 text-[13px] font-bold uppercase tracking-wide text-emerald-300">
                                    <ShieldCheck size={15} aria-hidden="true" /> Seguridad de la Cuenta
                                </h3>
                                <div className="grid grid-cols-3 gap-3">
                                    <SecurityTile icon={<ShieldCheck size={16} className="text-emerald-400" aria-hidden="true" />} label="Cuenta activa" />
                                    <SecurityTile icon={<Lock size={16} className="text-cyan-400" aria-hidden="true" />} label="Contraseña cifrada" />
                                    <SecurityTile
                                        icon={<Clock size={16} className="text-amber-400" aria-hidden="true" />}
                                        label="Último acceso"
                                        value={profile?.last_login ? new Date(profile.last_login).toLocaleDateString('es-EC') : '—'}
                                    />
                                </div>
                            </div>
                        </div>
                    </motion.aside>
                </React.Fragment>
            )}
        </AnimatePresence>
    );
}

function PasswordField({ label, value, onChange, show, onToggleShow, placeholder }) {
    return (
        <div>
            <label className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-white/40">{label}</label>
            <div className="relative">
                <input
                    type={show ? 'text' : 'password'}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 pr-10 text-[13px] text-white outline-none focus:border-cyan-500/40"
                />
                <button
                    type="button"
                    onClick={onToggleShow}
                    tabIndex={-1}
                    aria-label={show ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70"
                >
                    {show ? <EyeOff size={15} aria-hidden="true" /> : <Eye size={15} aria-hidden="true" />}
                </button>
            </div>
        </div>
    );
}

function SecurityTile({ icon, label, value }) {
    return (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-white/10 bg-black/30 px-3 py-4 text-center">
            {icon}
            <span className="text-[11px] font-bold uppercase leading-snug tracking-wide text-white/60">{label}</span>
            {value && <span className="text-[11px] text-white/40">{value}</span>}
        </div>
    );
}
