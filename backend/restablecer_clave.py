"""
backend/restablecer_clave.py — restablece la contraseña de una cuenta desde la consola.

Las contraseñas se guardan como hash bcrypt y no se pueden recuperar; este script
permite asignar una nueva cuando se olvidó. La clave se escribe oculta (getpass) y
nunca se imprime. Uso, desde la carpeta backend:

    venv\\Scripts\\python.exe restablecer_clave.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
"""
from getpass import getpass

from core import usuarios


def main() -> None:
    cuentas = usuarios.listar()
    if not cuentas:
        print('No hay cuentas registradas. Defina ADMIN_INICIAL_USUARIO y ADMIN_INICIAL_CLAVE en .env y reinicie el backend.')
        return
    print('Cuentas registradas:')
    for c in cuentas:
        print(f"  - {c['usuario']:<28} {c.get('rol', ''):<10} {'activa' if c.get('activo', True) else 'inactiva'}")
    usuario = input('\nUsuario a restablecer: ').strip().lower()
    if not any(c['usuario'] == usuario for c in cuentas):
        print('Ese usuario no existe.')
        return
    nueva = getpass('Nueva contraseña (mínimo 8 caracteres, no se muestra): ')
    if len(nueva) < 8:
        print('La contraseña debe tener al menos 8 caracteres.')
        return
    if getpass('Repita la contraseña: ') != nueva:
        print('Las contraseñas no coinciden.')
        return
    usuarios.actualizar(usuario, clave=nueva)
    print(f'Contraseña de "{usuario}" actualizada. Ya puede ingresar al sistema.')


if __name__ == '__main__':
    main()
