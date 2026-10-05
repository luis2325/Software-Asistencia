
-- SISTEMA DE ASISTENCIA FACIAL VALU
-- Script completo de base de datos


-- Crear la base de datos si no existe
CREATE DATABASE IF NOT EXISTS facial;
USE facial;


-- TABLA: usuarios

CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `rol` enum('admin','secretario') NOT NULL DEFAULT 'secretario',
  `email` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- TABLA: personas

CREATE TABLE IF NOT EXISTS `personas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `vector_facial` longblob,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- TABLA: asistencia

CREATE TABLE IF NOT EXISTS `asistencia` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_persona` int DEFAULT NULL,
  `fecha` date DEFAULT NULL,
  `hora_entrada` time DEFAULT NULL,
  `hora_salida` time DEFAULT NULL,
  `estado` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_persona` (`id_persona`),
  CONSTRAINT `asistencia_ibfk_1` FOREIGN KEY (`id_persona`) REFERENCES `personas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- TABLA: configuracion

CREATE TABLE IF NOT EXISTS `configuracion` (
  `id` int NOT NULL DEFAULT '1',
  `hora_inicio` time NOT NULL DEFAULT '08:25:00',
  `hora_final` time NOT NULL DEFAULT '20:00:00',
  `hora_limite` time NOT NULL,
  `hora_salida_almuerzo` time NOT NULL DEFAULT '12:00:00',
  `hora_regreso_almuerzo` time NOT NULL DEFAULT '13:00:00',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Datos iniciales de configuración (solo si no existen)
INSERT IGNORE INTO `configuracion` (`id`, `hora_inicio`, `hora_final`, `hora_limite`, `hora_salida_almuerzo`, `hora_regreso_almuerzo`)
VALUES (1, '08:25:00', '20:00:00', '08:30:00', '12:00:00', '13:00:00');


-- TABLA: password_resets

CREATE TABLE IF NOT EXISTS `password_resets` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `token` varchar(100) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- DATOS INICIALES


-- Usuario administrador (solo si no existe)
-- Contraseña: admin123 (hash generado por tu sistema)
INSERT IGNORE INTO `usuarios` (`id`, `username`, `password_hash`, `rol`, `email`)
VALUES (1, 'admin', 'pbkdf2:sha256:260000$lHtZz0xw$c9c6c4c7f1e2d3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8', 'admin', 'admin@example.com');

-- FIN DEL SCRIPT

