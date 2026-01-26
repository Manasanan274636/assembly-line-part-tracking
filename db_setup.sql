-- 1. Create Users Table
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL,
  `email` varchar(120) NOT NULL,
  `password_hash` varchar(128) DEFAULT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'operator',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Insert Default Users
-- Admin (Pass: admin123)
INSERT INTO `users` (`username`, `email`, `password_hash`, `role`)
VALUES ('admin', 'admin@example.com', 'scrypt:32768:8:1$KlcDD3PS7fBb5KvY$b04b851786f31797c6900777b71f5f6b786d5fce942f2a4e8630aa4dd5d767610644325ab61e2fceef60311517d6acf042154d04674ac281dbc12bc84eaccad1', 'admin');

-- Operator (Pass: op123)
INSERT INTO `users` (`username`, `email`, `password_hash`, `role`)
VALUES ('operator', 'operator@example.com', 'scrypt:32768:8:1$hGg42aZHXY3bgp1w$6ee08820c938615366838abc760e96a047f6fa47f9830d3e19e688854221f40906dc3552a040496af5f0c1002ed231d4ddcde7e1e2d7fda6ac9a105183b5dcdb', 'operator');
