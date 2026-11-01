CREATE DATABASE IF NOT EXISTS proyecto_ambulantes
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE proyecto_ambulantes;

CREATE TABLE IF NOT EXISTS vendedor (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_puesto VARCHAR(100) NOT NULL UNIQUE,
    tipo_negocio VARCHAR(100) NOT NULL DEFAULT 'Otro',
    descripcion_negocio VARCHAR(500) NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    telefono VARCHAR(25) NOT NULL,
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    estado TINYINT(1) NOT NULL DEFAULT 1,
    correo_verificado TINYINT(1) NOT NULL DEFAULT 0,
    codigo_verificacion VARCHAR(255) NULL,
    url_foto_puesto VARCHAR(255) NULL,
    horario VARCHAR(100) NOT NULL,
    vendiendo_hoy TINYINT(1) NOT NULL DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    id_vendedor INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_categoria_vendedor FOREIGN KEY (id_vendedor)
      REFERENCES vendedor(id) ON DELETE CASCADE,
    UNIQUE KEY uq_categoria_vendedor (id_vendedor, nombre)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS productos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_p VARCHAR(120) NOT NULL,
    descripcion TEXT NULL,
    precio DECIMAL(10,2) NOT NULL,
    foto_producto VARCHAR(255) NULL,
    id_categoria INT NOT NULL,
    id_vendedor INT NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_producto_categoria FOREIGN KEY (id_categoria)
      REFERENCES categorias(id) ON DELETE RESTRICT,
    CONSTRAINT fk_producto_vendedor FOREIGN KEY (id_vendedor)
      REFERENCES vendedor(id) ON DELETE CASCADE,
    INDEX idx_producto_vendedor (id_vendedor)
) ENGINE=InnoDB;

