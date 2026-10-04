# Manual de instalación — VicMar Data AI

**Última actualización:** 2026-10-03
**Para quién es:** cualquier persona que reciba el proyecto (clonado de GitHub, en una carpeta comprimida o en un pendrive) y necesite levantarlo completo —frontend, backend y base de datos— en otra computadora con Windows 10/11.

Siga los pasos en orden. Los comandos se escriben en PowerShell, uno a la vez.

---

## 1. Las tres piezas del sistema

| Pieza | Qué es | Dónde vive | Puerto |
|---|---|---|---|
| **Frontend** | La página web (React + Vite) | `codigo_fuente/frontend/` | `3000` |
| **Backend** | API FastAPI: modelo predictivo, NL2SQL, seguridad | `codigo_fuente/backend/` | `8090` |
| **Base de datos** | SQL Server 2022 en un contenedor Docker | contenedor `vicmar-sqlserver` | `1433` |

Las tres deben estar corriendo al mismo tiempo. El frontend habla con el backend y el backend con la base de datos. La carpeta `documentacion/` contiene el documento de titulación y no hace falta para levantar el sistema.

---

## 2. Requisitos

1. **Docker Desktop** — <https://www.docker.com/products/docker-desktop/>. Instalar, reiniciar si lo pide y abrirlo hasta que el ícono de la ballena deje de animarse.
2. **Node.js 20 LTS o superior** — <https://nodejs.org/>. Comprobar con `node --version`.
3. **Python 3.14** — <https://www.python.org/downloads/>. Marcar **«Add python.exe to PATH»** al instalar. Comprobar con `py -3.14 --version`.
4. **ODBC Driver 18 for SQL Server** — <https://learn.microsoft.com/es-es/sql/connect/odbc/download-odbc-driver-for-sql-server> (`msodbcsql.msi`).

---

## 3. Obtener el proyecto

- **Desde GitHub** (repositorio privado; requiere permiso de acceso):
  ```powershell
  git clone https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI.git
  cd PROYECTO-TITULACION-MARLON-VICTOR-UNEMI
  ```
- **Desde una copia:** copiar la carpeta del proyecto **sin** `node_modules/`, `venv/` ni `dist/`, que se regeneran en la computadora nueva.

---

## 4. Configuración local (archivos que no se versionan)

```powershell
copy codigo_fuente\backend\.env.example codigo_fuente\backend\.env
copy codigo_fuente\backend\usuarios_prueba.example.json codigo_fuente\backend\usuarios_prueba.local.json
```

Edite `codigo_fuente\backend\.env` con el Bloc de notas:
- **`DB_PASSWORD`**: contraseña del usuario `sa` de SQL Server (la que se use al crear el contenedor en el paso 5).
- **`CHAT_READER_PASSWORD`**: contraseña del usuario de solo lectura con el que se ejecuta el SQL que genera la IA.
- Al menos una clave de proveedor de IA gratuita: `GEMINI_API_KEY`, `GROQ_API_KEY` o `NVIDIA_API_KEY`. Sin ninguna, el sistema funciona, pero el chat en lenguaje natural responde con un aviso.

Edite `usuarios_prueba.local.json` con las contraseñas de los usuarios de prueba (una por rol). Las contraseñas reales de la demostración se entregan aparte.

---

## 5. Base de datos

### Opción A — Reconstruir todo con el pipeline (recomendada)

1. Crear el contenedor de SQL Server con la misma contraseña de `DB_PASSWORD`:
   ```powershell
   docker run -d --name vicmar-sqlserver --restart unless-stopped -p 1433:1433 -e ACCEPT_EULA=Y -e MSSQL_PID=developer -e MSSQL_SA_PASSWORD=SU_CONTRASEÑA mcr.microsoft.com/mssql/server:2022-latest
   ```
2. Descargar el dataset público OULAD en `datos/externos/oulad/` (ver [`datos/README.md`](../../datos/README.md)).
3. Crear el entorno de Python e instalar dependencias:
   ```powershell
   py -3.14 -m venv codigo_fuente\backend\venv
   codigo_fuente\backend\venv\Scripts\pip install -r codigo_fuente\backend\requirements.txt
   ```
4. Ejecutar el pipeline completo desde la raíz del repositorio:
   ```powershell
   powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1
   ```
   Carga los datos de prueba anonimizados de UNEMI y la institución OULAD, crea el almacén en esquema estrella con sus vistas y el usuario `chat_reader`, ejecuta el ETL, entrena, califica y segmenta por institución, carga los referentes externos, genera el diccionario de datos y corre las pruebas. Cada paso se detiene si el anterior falló.

### Opción B — Mover el contenedor ya cargado (archivo `.tar`)

En la computadora original:
```powershell
docker commit vicmar-sqlserver vicmar-sqlserver-portable:ultima
docker save -o vicmar-sqlserver-backup.tar vicmar-sqlserver-portable:ultima
```
En la computadora nueva:
```powershell
docker load -i vicmar-sqlserver-backup.tar
docker run -d --name vicmar-sqlserver --restart unless-stopped -p 1433:1433 vicmar-sqlserver-portable:ultima
```
Las contraseñas de `sa` y `chat_reader` son las del contenedor original.

---

## 6. Usuarios de la aplicación

Los usuarios para iniciar sesión viven en `codigo_fuente\backend\security_config.json` (no se versiona). Para crearlos:
```powershell
cd codigo_fuente\backend
venv\Scripts\python.exe scripts\fijar_passwords_prueba.py
cd ..\..
```
El script toma las contraseñas de `usuarios_prueba.local.json`. Para la demostración se usa el usuario con rol **ACADÉMICO**.

---

## 7. Levantar el sistema

Instalar las dependencias del frontend (solo la primera vez):
```powershell
cd codigo_fuente\frontend
npm install
```
En una terminal, el backend:
```powershell
cd codigo_fuente\frontend
npm run dev:backend
```
En otra terminal, el frontend:
```powershell
cd codigo_fuente\frontend
npm run dev
```
Abrir <http://localhost:3000>. El backend responde en <http://127.0.0.1:8090/api/health>.

El pipeline también puede levantar ambos al final: `demo_tesis.ps1 -Levantar`.

---

## 8. Verificación

1. **Inicio de sesión** con el usuario académico.
2. **Conexión** a `UNEMI_PRUEBAS`: el panel muestra matrícula, riesgo de abandono con sus factores y la confiabilidad del modelo.
3. **Inteligencia institucional:** segmentos de carreras y referentes externos con DOI.
4. **Chat:** «¿Cuántos estudiantes están en riesgo alto por carrera?» responde con cifras.
5. **Aislamiento:** al conectar `OULAD_UK` solo aparecen datos de esa institución.

---

## 9. Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| Error con `pyodbc` u `ODBC Driver` al iniciar el backend | Falta el ODBC Driver 18 | Instalarlo (paso 2.4) y reiniciar la terminal |
| El panel aparece en `0` con un aviso rojo | El contenedor no está corriendo o `DB_PASSWORD` no coincide | `docker ps`; revisar `codigo_fuente\backend\.env` |
| El chat responde siempre con un aviso | No hay ninguna clave de proveedor de IA en `.env` | Agregar al menos una clave gratuita |
| Puerto `1433`, `3000` u `8090` ocupado | Otro programa usa el puerto | Cambiar el mapeo de Docker (`-p 14330:1433` y `DB_HOST=localhost,14330`), el `port` de `vite.config.ts` o el `--port` de `dev:backend` junto con `VITE_BACKEND_URL` |
| `ModuleNotFoundError` en un script | Se usó el Python del sistema | Ejecutar con `venv\Scripts\python.exe` |
| El pipeline se detiene en OULAD | Faltan los CSV en `datos/externos/oulad/` | Descargarlos (ver `datos/README.md`) |

---

## 10. Privacidad de los datos

- Los datos de prueba de UNEMI (`codigo_fuente/base_de_datos/datos_de_prueba/`) son **sintéticos y anonimizados**: las cédulas usan el código de provincia «00», que el Registro Civil no asigna, y los nombres son ficticios. No se guarda ninguna tabla de correspondencia con datos reales.
- Los datos personales originales que sirvieron de base para el dataset **no forman parte del proyecto** y no se distribuyen.
- OULAD es un dataset público y anónimo (CC BY 4.0).
- Antes de enviar filas a un proveedor externo de IA, el sistema reemplaza cédulas y nombres por seudónimos (`codigo_fuente/backend/core/privacidad.py`).
- Las credenciales (`.env`, `security_config.json`, `usuarios_prueba.local.json`) nunca se suben al repositorio.

---

## 11. Comandos de referencia rápida

```powershell
docker start vicmar-sqlserver                      # base de datos
cd codigo_fuente\frontend; npm run dev:backend     # backend (terminal 1)
cd codigo_fuente\frontend; npm run dev             # frontend (terminal 2)
docker stop vicmar-sqlserver                       # apagar la base de datos
```
