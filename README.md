# Nexum ID — Plataforma de Inteligencia Biométrica & Control de Asistencia

![Version](https://img.shields.io/badge/version-2.0.0--enterprise-indigo)
![Security](https://img.shields.io/badge/security-hardened-emerald)
![Mobile](https://img.shields.io/badge/mobile-WebRTC%20%7C%20PWA-cyan)

**Nexum ID** es una solución tecnológica avanzada para el registro, verificación facial y control de jornadas laborales y asistencia. Diseñada con estándares de software SaaS moderno, opera fluidamente tanto en computadores de escritorio como en dispositivos móviles (smartphones y tablets) mediante visión computacional WebRTC y arquitectura en la nube.

---

## 🚀 Características Principales

* 📱 **Acceso Móvil Nativo & WebRTC**:
  * Escaneo facial directamente desde la cámara frontal del teléfono celular (Chrome / Safari).
  * Soporte PWA (Progressive Web App): instalable como aplicación nativa en Android e iOS ("Añadir a pantalla de inicio").
  * Visor HUD biométrico animado con esquinas de enfoque, láser de escaneo y retroalimentación háptica (vibración).
* 🛡️ **Seguridad Empresarial Reforzada**:
  * Eliminación de credenciales expuestas: gestión de secretos mediante variables de entorno en `.env`.
  * Protección universal contra ataques Cross-Site Request Forgery (CSRF).
  * Serialización binaria segura de vectores faciales con NumPy (eliminación de vulnerabilidades de deserialización arbitraria).
  * Hashing criptográfico de contraseñas con PBKDF2:SHA256 y tokens de un solo uso.
* ⚡ **Arquitectura de Base de Datos Híbrida**:
  * Compatible con **MySQL local** con Connection Pooling.
  * Preparado para migración a **Supabase (PostgreSQL)** con extensión nativa `pgvector` e indexación HNSW para búsquedas faciales en menos de 5 ms.
* 📊 **Panel Ejecutivo y Analítica en Tiempo Real**:
  * Dashboard con KPIs de asistencia, incidencias de puntualidad y cumplimiento.
  * Gráficos estadísticos interactivos con degradados y actualización automática.
  * Control de tolerancias horarias y exportación de reportes a formato CSV / Excel.

---

## 🛠️ Instalación y Puesta en Marcha

### 1. Clonar el Repositorio y Configurar Entorno
```bash
# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno
Copia la plantilla `.env.example` como `.env` y ajusta tus credenciales locales:
```bash
cp .env.example .env
```

### 3. Inicializar la Base de Datos
* **Opción Local (MySQL)**: Importa el archivo `database.sql` en tu servidor MySQL.
* **Opción Cloud (Supabase / PostgreSQL)**: Crea un proyecto gratuito en [Supabase.com](https://supabase.com), ve al editor SQL y ejecuta el script `supabase_schema.sql`. Luego coloca tu `DATABASE_URL` en `.env`.

### 4. Ejecutar el Servidor
```bash
python facial/app.py
```
El servidor iniciará en `http://0.0.0.0:5000`.

---

## 📱 Cómo Usarlo desde el Celular

1. Conecta tu teléfono celular a la misma red WiFi de tu computadora.
2. Averigua la IP local de tu computador (ejemplo: `192.168.1.15`).
3. Abre el navegador en tu teléfono (Chrome o Safari) e ingresa a:
   ```
   http://192.168.1.15:5000
   ```
4. Inicia sesión con tus credenciales de administrador o supervisor.
5. Ve a **"Marcar Asistencia"**, permite el acceso a la cámara frontal y encuadra tu rostro dentro del óvalo para registrar tu entrada o salida.
6. Pulsa en el menú del navegador **"Agregar a la pantalla de inicio"** para usarla como una aplicación instalada.

---

## 🏢 Estructura del Proyecto

```
Software-Asistencia/
├── .env                       # Variables de entorno seguras (ignorado en Git)
├── .env.example               # Plantilla de configuración
├── requirements.txt           # Dependencias fijadas
├── database.sql               # Esquema de base de datos MySQL corregido
├── supabase_schema.sql        # Esquema cloud PostgreSQL con pgvector
├── facial/
│   ├── app.py                 # Núcleo Flask, enrutador y API REST
│   ├── config.py              # Gestor de configuración desacoplado
│   ├── db_connection.py       # Conexión MySQL con Connection Pooling
│   ├── detector.py            # Motor biométrico WebRTC para celulares
│   ├── personas.py            # Módulo de registro facial seguro
│   ├── asistencia.py          # Lógica de cálculo de horarios y puntualidad
│   └── auth.py                # Autenticación, roles y recuperación de cuentas
├── static/
│   ├── theme.css              # Sistema de diseño Dark Slate & Electric Indigo
│   ├── manifest.json          # Manifiesto PWA para instalación móvil
│   └── sw.js                  # Service Worker
└── templates/                 # Plantillas HTML con diseño SaaS responsivo
```

---

© 2026 Nexum ID. Todos los derechos reservados.
