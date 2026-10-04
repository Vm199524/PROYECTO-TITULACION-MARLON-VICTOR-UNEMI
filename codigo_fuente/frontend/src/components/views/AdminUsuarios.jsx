/**
 * Archivo: AdminUsuarios.jsx
 * Rol: panel "Pizarra" de administración de usuarios (Fase 5, 28/08/2026,
 * — patrón portado conceptualmente de
 * TripleA_VentasIA: app/auth/routes.py + templates/auth/*.html, adaptado a
 * React/FastAPI y a los colores oscuros de VicMar Data AI).
 *
 * Un solo componente cubre "Usuarios" (lista) y "Nuevo Usuario" (alta):
 * ambos ítems del sidebar apuntan aquí con un `initialMode` distinto. La
 * edición se abre inline en el mismo panel (nunca un popup pequeño, a
 * requisito explícito).
 *
 * Roles y módulos: security_config.json YA tiene un catálogo de roles con
 * sus módulos habilitados — este panel no inventa un sistema de permisos
 * nuevo, solo hace CRUD de usuarios sobre ESE catálogo (GET /api/admin/roles).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Camera, Check, Eye, EyeOff, KeyRound, Lock, Pencil, Plus, Shield,
    ShieldOff, Trash2, UserPlus, Users, X,
} from 'lucide-react';
import { apiDelete, apiGet, apiPost, apiPut } from '../../services/api';
import { roleLabel } from '../../utils/roles';

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
                canvas.getContext('2d').drawImage(img, sx, sy, size, size, 0, 0, target, target);
                resolve(canvas.toDataURL('image/jpeg', 0.85));
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });
}

const COLOR_ROL = {
    ADMINISTRADOR: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
    CONTABILIDAD: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    RRHH: 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300',
    LOGISTICA: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    ACADEMICO: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
    GUEST: 'border-white/20 bg-white/5 text-white/50',
};

const colorRol = (rol) => COLOR_ROL[rol] || 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300';

// Catálogo de motores de IA seleccionables (30/08/2026) — espejo del que
// usa ChatInput.jsx para el selector del chat, pero aquí sirve para que un
// administrador decida qué motores puede elegir cada usuario en ese
// selector. El motor Pro ya no se ofrece desde el 01/09/2026 (igual que en
// el selector del chat); aquí se conceden los proveedores puntuales de la
// cascada (para probar cada API por separado). "flash" no se muestra como
// casilla: todos los roles lo tienen siempre, por diseño.
const MODELOS_IA_EDITABLES = [
    { id: 'gemini', label: 'Gemini', desc: 'Google · principal de la cascada' },
    { id: 'groq', label: 'Groq', desc: 'Respaldo #2 de la cascada' },
    { id: 'nvidia_deepseek_pro', label: 'DeepSeek V4 Pro', desc: 'NVIDIA NIM' },
    { id: 'nvidia_deepseek_flash', label: 'DeepSeek V4 Flash', desc: 'NVIDIA NIM' },
    { id: 'nvidia_kimi', label: 'Kimi K3', desc: 'NVIDIA NIM' },
    { id: 'nvidia_nemotron', label: 'Nemotron', desc: 'NVIDIA NIM' },
    { id: 'nvidia_muse', label: 'Muse Glimmer', desc: 'NVIDIA NIM' },
];

function formatFecha(iso, conHora = false) {
    if (!iso) return '—';
    try {
        return conHora
            ? new Date(iso).toLocaleString('es-EC', { dateStyle: 'short', timeStyle: 'short' })
            : new Date(iso).toLocaleDateString('es-EC');
    } catch {
        return '—';
    }
}

export function AdminUsuarios({ userAuth, initialMode = 'list' }) {
    const [modo, setModo] = useState(initialMode); // 'list' | 'create' | 'edit'
    const [usuarios, setUsuarios] = useState([]);
    const [roles, setRoles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [editando, setEditando] = useState(null); // username en edición

    useEffect(() => { setModo(initialMode); }, [initialMode]);

    const cargar = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [uRes, rRes] = await Promise.all([
                apiGet('/admin/users'),
                apiGet('/admin/roles'),
            ]);
            setUsuarios(uRes.data?.users || []);
            setRoles(rRes.data?.roles || []);
        } catch (err) {
            setError(err?.response?.data?.detail || 'No se pudo cargar la gestión de usuarios.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { cargar(); }, [cargar]);

    const alGuardar = () => {
        setModo('list');
        setEditando(null);
        cargar();
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            className="h-full w-full overflow-y-auto p-4 lg:p-6 custom-scrollbar"
        >
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-4">
                <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                    <h1 className="flex items-center gap-2 text-xl font-black uppercase tracking-tight text-white lg:text-2xl">
                        {modo === 'list' ? <Users size={28} className="text-cyan-400" aria-hidden="true" /> : <UserPlus size={28} className="text-cyan-400" aria-hidden="true" />}
                        {modo === 'create' ? 'Nuevo Usuario' : modo === 'edit' ? 'Editar Usuario' : 'Gestión de Usuarios'}
                    </h1>
                    {modo === 'list' ? (
                        <button
                            type="button"
                            onClick={() => setModo('create')}
                            className="flex items-center gap-2 self-start rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-4 py-2 text-[13px] font-bold uppercase tracking-wide text-cyan-300 transition-colors hover:bg-cyan-500/20"
                        >
                            <Plus size={15} aria-hidden="true" /> Nuevo Usuario
                        </button>
                    ) : (
                        <button
                            type="button"
                            onClick={() => { setModo('list'); setEditando(null); }}
                            className="flex items-center gap-2 self-start rounded-xl border border-white/10 bg-black/40 px-4 py-2 text-[13px] font-bold uppercase tracking-wide text-white/60 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
                        >
                            <X size={15} aria-hidden="true" /> Volver a la lista
                        </button>
                    )}
                </header>

                {error && (
                    <div role="alert" className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-3 text-[13px] text-rose-300">
                        {error}
                    </div>
                )}

                {modo === 'list' && (
                    <TablaUsuarios
                        usuarios={usuarios}
                        loading={loading}
                        userAuth={userAuth}
                        onEditar={(username) => { setEditando(username); setModo('edit'); }}
                        onCambio={cargar}
                    />
                )}

                {modo === 'create' && (
                    <FormularioUsuario roles={roles} onGuardado={alGuardar} onCancelar={() => setModo('list')} />
                )}

                {modo === 'edit' && (
                    <FormularioUsuario
                        roles={roles}
                        usuario={usuarios.find((u) => u.username === editando)}
                        onGuardado={alGuardar}
                        onCancelar={() => { setModo('list'); setEditando(null); }}
                    />
                )}
            </div>
        </motion.div>
    );
}

function TablaUsuarios({ usuarios, loading, userAuth, onEditar, onCambio }) {
    const [ocupado, setOcupado] = useState('');

    const alternarActivo = async (u) => {
        setOcupado(u.username);
        try {
            await apiPut(`/admin/users/${encodeURIComponent(u.username)}`, { active: !u.active });
            onCambio();
        } catch (err) {
            alert(err?.response?.data?.detail || 'No se pudo cambiar el estado del usuario.');
        } finally {
            setOcupado('');
        }
    };

    const eliminar = async (u) => {
        if (!window.confirm(`¿Eliminar al usuario "${u.username}"? Esta acción no se puede deshacer.`)) return;
        setOcupado(u.username);
        try {
            await apiDelete(`/admin/users/${encodeURIComponent(u.username)}`);
            onCambio();
        } catch (err) {
            alert(err?.response?.data?.detail || 'No se pudo eliminar el usuario.');
        } finally {
            setOcupado('');
        }
    };

    if (loading) {
        return <div className="rounded-[32px] border border-white/10 p-10 text-center text-white/40 shadow-2xl" style={{ background: 'rgba(255,255,255,0.02)' }}>Cargando usuarios…</div>;
    }
    if (!usuarios.length) {
        return <div className="rounded-[32px] border border-white/10 p-10 text-center text-white/40 shadow-2xl" style={{ background: 'rgba(255,255,255,0.02)' }}>Todavía no hay usuarios registrados.</div>;
    }

    // Misma tarjeta que TableCard en Indicadores (BentoDashboard): el borde
    // redondeado con 32px de padding es el que da el "colchón" antes del
    // contenido. Antes esta tabla usaba SU PROPIO borde como contenedor de
    // scroll, así que el texto quedaba pegado al borde de la tarjeta — la
    // regla visual pedida por el usuario: nada debe tocar el perímetro de
    // su tarjeta/caja.
    return (
        <div className="rounded-[32px] border border-white/10 p-6 shadow-2xl sm:p-8" style={{ background: 'rgba(255,255,255,0.02)' }}>
            <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-[13px]">
                <thead>
                    <tr className="border-b border-white/10 text-[11px] font-bold uppercase tracking-wider text-white/40">
                        <th className="px-4 py-3">Usuario</th>
                        <th className="px-4 py-3">Nombre</th>
                        <th className="px-4 py-3">Correo</th>
                        <th className="px-4 py-3">Rol</th>
                        <th className="px-4 py-3">Estado</th>
                        <th className="px-4 py-3">Último acceso</th>
                        <th className="px-4 py-3">Creado</th>
                        <th className="px-4 py-3 text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {usuarios.map((u) => {
                        const esUnoMismo = u.username === (userAuth?.username || '');
                        // Cuenta del desarrollador (bandera `protected` del backend).
                        // Para cualquier otro administrador, esa fila no ofrece
                        // acciones: ni editar, ni desactivar, ni eliminar. El
                        // backend rechaza igual esas operaciones con 403 — aquí
                        // solo se evita mostrar un botón que nunca va a funcionar.
                        const bloqueadaPorSerDesarrollador = !!u.protected && !esUnoMismo;
                        return (
                            <tr key={u.username} className="border-b border-white/5 text-white/80 last:border-0 hover:bg-white/[0.03]">
                                <td className="px-4 py-3 font-mono text-cyan-300/90">{u.username}</td>
                                <td className="px-4 py-3 font-bold text-white">{u.name}</td>
                                <td className="px-4 py-3 text-white/50">{u.email || '—'}</td>
                                <td className="px-4 py-3">
                                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${colorRol(u.role)}`}>
                                        <Shield size={11} aria-hidden="true" /> {roleLabel(u.role)}
                                    </span>
                                </td>
                                <td className="px-4 py-3">
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide ${u.active ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-white/15 bg-white/5 text-white/40'}`}>
                                        {u.active ? 'Activo' : 'Inactivo'}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-white/50">{formatFecha(u.last_login, true)}</td>
                                <td className="px-4 py-3 text-white/50">{formatFecha(u.created_at)}</td>
                                <td className="px-4 py-3">
                                    <div className="flex items-center justify-end gap-1.5">
                                        {bloqueadaPorSerDesarrollador ? (
                                            <span
                                                title="Cuenta del desarrollador del sistema: protegida"
                                                className="inline-flex items-center gap-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-violet-300"
                                            >
                                                <Lock size={11} aria-hidden="true" /> Protegida
                                            </span>
                                        ) : (
                                        <>
                                        <button
                                            type="button"
                                            onClick={() => onEditar(u.username)}
                                            title="Editar"
                                            aria-label={`Editar ${u.username}`}
                                            className="flex h-7 w-7 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 transition-colors hover:bg-cyan-500/20"
                                        >
                                            <Pencil size={13} aria-hidden="true" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => alternarActivo(u)}
                                            disabled={esUnoMismo || ocupado === u.username}
                                            title={esUnoMismo ? 'No puedes cambiar tu propio estado' : (u.active ? 'Desactivar' : 'Activar')}
                                            aria-label={u.active ? `Desactivar ${u.username}` : `Activar ${u.username}`}
                                            className="flex h-7 w-7 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-30"
                                        >
                                            {u.active ? <ShieldOff size={13} aria-hidden="true" /> : <Shield size={13} aria-hidden="true" />}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => eliminar(u)}
                                            disabled={esUnoMismo || ocupado === u.username}
                                            title={esUnoMismo ? 'No puedes eliminarte a ti mismo' : 'Eliminar'}
                                            aria-label={`Eliminar ${u.username}`}
                                            className="flex h-7 w-7 items-center justify-center rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 transition-colors hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-30"
                                        >
                                            {esUnoMismo ? <Lock size={12} aria-hidden="true" /> : <Trash2 size={13} aria-hidden="true" />}
                                        </button>
                                        </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            </div>
        </div>
    );
}

function FormularioUsuario({ roles, usuario = null, onGuardado, onCancelar }) {
    const esEdicion = Boolean(usuario);
    const [nombre, setNombre] = useState(usuario?.name || '');
    const [username, setUsername] = useState(usuario?.username || '');
    const [correo, setCorreo] = useState(usuario?.email || '');
    const [rol, setRol] = useState(usuario?.role || roles[0]?.role || '');
    // Modelos de IA permitidos (30/08/2026): override por usuario, aparte
    // del rol — así un usuario puntual puede tener un motor adicional sin
    // cambiar todo su rol. Al editar arranca con lo que el backend ya resolvió
    // (default del rol si no había override); al crear arranca vacío y el
    // backend aplica el default del rol elegido.
    const [modelosIA, setModelosIA] = useState(usuario?.modelos_permitidos || []);
    const alternarModeloIA = (clave) => {
        setModelosIA((prev) => (
            prev.includes(clave) ? prev.filter((m) => m !== clave) : [...prev, clave]
        ));
    };
    const [password, setPassword] = useState('');
    const [confirmar, setConfirmar] = useState('');
    const [mostrarPwd, setMostrarPwd] = useState(false);
    const [avatar, setAvatar] = useState(usuario?.avatar || null);
    const [guardando, setGuardando] = useState(false);
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        if (!rol && roles.length) setRol(roles[0].role);
    }, [roles, rol]);

    const seleccionarFoto = async (e) => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        try {
            setAvatar(await resizeImageToDataUrl(file));
        } catch {
            setErrorMsg('No se pudo procesar esa imagen.');
        }
    };

    const guardar = async (e) => {
        e.preventDefault();
        setErrorMsg('');

        if (!esEdicion) {
            if (!username.trim() || !nombre.trim()) { setErrorMsg('Usuario y nombre completo son obligatorios.'); return; }
            if (password.length < 8) { setErrorMsg('La contraseña debe tener mínimo 8 caracteres.'); return; }
            if (password !== confirmar) { setErrorMsg('Las contraseñas no coinciden.'); return; }
        } else if (password || confirmar) {
            if (password.length < 8) { setErrorMsg('La nueva contraseña debe tener mínimo 8 caracteres.'); return; }
            if (password !== confirmar) { setErrorMsg('Las contraseñas no coinciden.'); return; }
        }

        // Flash está siempre incluido de fondo: no se muestra como casilla
        // (todos los roles lo tienen por diseño), pero si se marcó otro motor
        // hay que enviarlo igual junto a él para no dejar al usuario sin el
        // básico.
        const modelosFinales = modelosIA.includes('flash') ? modelosIA : ['flash', ...modelosIA];

        setGuardando(true);
        try {
            if (esEdicion) {
                await apiPut(`/admin/users/${encodeURIComponent(usuario.username)}`, {
                    name: nombre.trim(),
                    email: correo.trim(),
                    role: rol,
                    new_password: password || null,
                    avatar: avatar && avatar !== usuario.avatar ? avatar : null,
                    modelos_permitidos: modelosFinales,
                });
            } else {
                await apiPost('/admin/users', {
                    username: username.trim(),
                    name: nombre.trim(),
                    email: correo.trim(),
                    password,
                    role: rol,
                    avatar: avatar || null,
                    modelos_permitidos: modelosIA.length ? modelosFinales : null,
                });
            }
            onGuardado();
        } catch (err) {
            setErrorMsg(err?.response?.data?.detail || 'No se pudo guardar el usuario.');
        } finally {
            setGuardando(false);
        }
    };

    if (esEdicion && !usuario) {
        return <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-10 text-center text-white/40">Usuario no encontrado.</div>;
    }

    return (
        <form onSubmit={guardar} className="mx-auto flex w-full max-w-2xl flex-col gap-5">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
                <div className="mx-auto mb-5 h-20 w-20 overflow-hidden rounded-full border-2 border-cyan-500/40 bg-cyan-500/10">
                    {avatar ? (
                        <img src={avatar} alt="" className="h-full w-full object-cover" />
                    ) : (
                        <div className="flex h-full w-full items-center justify-center text-xl font-black text-cyan-300">
                            {(nombre || username || 'U').slice(0, 1).toUpperCase()}
                        </div>
                    )}
                </div>
                <label className="mx-auto flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-[12px] font-bold uppercase tracking-wide text-white/70 transition-colors hover:border-cyan-500/40 hover:text-cyan-300">
                    <Camera size={14} aria-hidden="true" /> Foto de perfil (opcional)
                    <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={seleccionarFoto} />
                </label>

                <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <Campo label="Nombre completo">
                        <input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Juan Pérez" className="campo-input" required />
                    </Campo>
                    <Campo label="Usuario">
                        <input
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="juan.perez"
                            disabled={esEdicion}
                            className="campo-input disabled:opacity-50"
                            required
                        />
                    </Campo>
                    <Campo label="Correo electrónico">
                        <input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} placeholder="juan@empresa.com" className="campo-input" />
                    </Campo>
                    <Campo label="Rol">
                        <div className="flex flex-wrap gap-2">
                            {roles.map((r) => (
                                <button
                                    key={r.role}
                                    type="button"
                                    onClick={() => setRol(r.role)}
                                    title={r.description}
                                    className={`rounded-lg border px-3 py-2 text-[12px] font-bold uppercase tracking-wide transition-colors ${
                                        rol === r.role ? colorRol(r.role) : 'border-white/10 bg-black/30 text-white/50 hover:text-white/80'
                                    }`}
                                >
                                    {roleLabel(r.role)}
                                </button>
                            ))}
                        </div>
                    </Campo>
                    <Campo label="Motores de IA adicionales (Flash siempre incluido)">
                        <div className="flex flex-wrap gap-2">
                            {MODELOS_IA_EDITABLES.map((m) => {
                                const activo = modelosIA.includes(m.id);
                                return (
                                    <button
                                        key={m.id}
                                        type="button"
                                        onClick={() => alternarModeloIA(m.id)}
                                        title={m.desc}
                                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[12px] font-bold uppercase tracking-wide transition-colors ${
                                            activo ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-300' : 'border-white/10 bg-black/30 text-white/50 hover:text-white/80'
                                        }`}
                                    >
                                        {activo ? <Check size={12} aria-hidden="true" /> : null}
                                        {m.label}
                                    </button>
                                );
                            })}
                        </div>
                    </Campo>
                    <Campo label={esEdicion ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña'}>
                        <div className="relative">
                            <input
                                type={mostrarPwd ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Mínimo 8 caracteres"
                                className="campo-input pr-10"
                                required={!esEdicion}
                            />
                            <button type="button" onClick={() => setMostrarPwd((v) => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70">
                                {mostrarPwd ? <EyeOff size={15} aria-hidden="true" /> : <Eye size={15} aria-hidden="true" />}
                            </button>
                        </div>
                    </Campo>
                    <Campo label="Confirmar contraseña">
                        <input
                            type={mostrarPwd ? 'text' : 'password'}
                            value={confirmar}
                            onChange={(e) => setConfirmar(e.target.value)}
                            placeholder="Repite la contraseña"
                            className="campo-input"
                            required={!esEdicion && Boolean(password)}
                        />
                    </Campo>
                </div>

                {errorMsg && <p className="mt-4 text-[13px] text-rose-400">{errorMsg}</p>}

                <div className="mt-6 flex gap-3">
                    <button
                        type="submit"
                        disabled={guardando}
                        className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 py-3 text-[13px] font-bold uppercase tracking-wide text-black transition-colors hover:bg-cyan-400 disabled:opacity-40"
                    >
                        {esEdicion ? <Check size={15} aria-hidden="true" /> : <UserPlus size={15} aria-hidden="true" />}
                        {guardando ? 'Guardando…' : esEdicion ? 'Guardar Cambios' : 'Crear Usuario'}
                    </button>
                    <button
                        type="button"
                        onClick={onCancelar}
                        className="rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-[13px] font-bold uppercase tracking-wide text-white/60 hover:text-white"
                    >
                        Cancelar
                    </button>
                </div>
            </div>
        </form>
    );
}

function Campo({ label, children }) {
    return (
        <div className="flex flex-col gap-1.5">
            <label className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-white/40">
                <KeyRound size={0} className="hidden" /> {label}
            </label>
            {children}
        </div>
    );
}
