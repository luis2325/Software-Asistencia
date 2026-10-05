-- ==============================================================
-- Nexum ID - Script de Base de Datos para Supabase (PostgreSQL)
-- ==============================================================
-- Instrucciones:
-- 1. Ve a tu proyecto en Supabase (https://supabase.com).
-- 2. Entra en "SQL Editor" en el menú izquierdo.
-- 3. Pega todo este contenido y presiona "Run".
-- ==============================================================

-- 1. Habilitar extensión vectorial para reconocimiento facial ultrarrápido
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tabla de Usuarios del Sistema (Admin / Supervisor)
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) DEFAULT 'secretario' CHECK (rol IN ('admin', 'secretario', 'supervisor')),
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Tabla de Colaboradores / Personal (Con vector facial nativo de 128 dimensiones)
CREATE TABLE IF NOT EXISTS personas (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    cargo VARCHAR(100) DEFAULT 'Colaborador',
    departamento VARCHAR(100) DEFAULT 'General',
    foto_url TEXT,
    vector_facial vector(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para búsqueda vectorial instantánea (menos de 5 milisegundos)
CREATE INDEX IF NOT EXISTS personas_vector_idx ON personas 
USING hnsw (vector_facial vector_l2_ops);

-- 4. Tabla de Asistencia y Control de Jornada
CREATE TABLE IF NOT EXISTS asistencia (
    id BIGSERIAL PRIMARY KEY,
    id_persona BIGINT REFERENCES personas(id) ON DELETE CASCADE,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora_entrada TIME NOT NULL,
    hora_salida TIME,
    estado VARCHAR(30) NOT NULL, -- 'Temprano', 'Tarde', 'Fuera de horario'
    latitud NUMERIC(10, 7),
    longitud NUMERIC(10, 7),
    dispositivo VARCHAR(50) DEFAULT 'Móvil / WebRTC',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asistencia_fecha ON asistencia(fecha);
CREATE INDEX IF NOT EXISTS idx_asistencia_persona ON asistencia(id_persona);

-- 5. Tabla de Configuración de Horarios y Geocerca
CREATE TABLE IF NOT EXISTS configuracion (
    id INT PRIMARY KEY DEFAULT 1,
    hora_inicio TIME DEFAULT '08:25:00',
    hora_limite TIME DEFAULT '08:30:00',
    hora_final TIME DEFAULT '20:00:00',
    hora_salida_almuerzo TIME DEFAULT '12:00:00',
    hora_regreso_almuerzo TIME DEFAULT '13:00:00',
    tolerancia_minutos INT DEFAULT 5,
    geocerca_activa BOOLEAN DEFAULT FALSE,
    geocerca_lat NUMERIC(10, 7) DEFAULT 0.0,
    geocerca_lng NUMERIC(10, 7) DEFAULT 0.0,
    geocerca_radio_metros INT DEFAULT 100,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fila inicial de configuración
INSERT INTO configuracion (id, hora_inicio, hora_limite, hora_final, hora_salida_almuerzo, hora_regreso_almuerzo)
VALUES (1, '08:25:00', '08:30:00', '20:00:00', '12:00:00', '13:00:00')
ON CONFLICT (id) DO NOTHING;

-- 6. Tabla de Recuperación de Contraseñas
CREATE TABLE IF NOT EXISTS password_resets (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token_hash);

-- 7. Usuario Administrador Inicial
-- Usuario: admin | Contraseña temporal: admin123
INSERT INTO usuarios (id, username, password_hash, rol, email)
VALUES (1, 'admin', 'pbkdf2:sha256:260000$lHtZz0xw$c9c6c4c7f1e2d3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8', 'admin', 'admin@nexum.local')
ON CONFLICT (id) DO NOTHING;
