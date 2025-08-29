-- Criação do banco de dados
CREATE DATABASE IF NOT EXISTS telegram_financas_bot;
USE telegram_financas_bot;

-- Tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    first_name VARCHAR(255),
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de categorias
CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de transações
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    type ENUM('entrada', 'despesa') NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    category_id INT,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Tabela de mensalidades
CREATE TABLE IF NOT EXISTS mensalidades (
    mensalidade_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    payment_id VARCHAR(255) NOT NULL UNIQUE,
    valor DECIMAL(10,2) NOT NULL,
    status ENUM('pendente', 'pago', 'cancelado', 'expirado') DEFAULT 'pendente',
    data_pagamento TIMESTAMP NULL,
    dias_validade INT DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Inserir categorias padrão
INSERT IGNORE INTO categories (name) VALUES 
('Mensalidade'),
('Alimentação'),
('Transporte'),
('Moradia'),
('Lazer'),
('Saúde'),
('Educação'),
('Vestuário'),
('Outros');

-- Criar índices para melhor performance
CREATE INDEX idx_user_id ON transactions(user_id);
CREATE INDEX idx_transaction_date ON transactions(transaction_date);
CREATE INDEX idx_payment_id ON mensalidades(payment_id);
CREATE INDEX idx_user_status ON mensalidades(user_id, status);
