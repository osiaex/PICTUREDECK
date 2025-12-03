-- Create database if not exists
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS aigc
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE aigc;

DROP TABLE IF EXISTS collections;
DROP TABLE IF EXISTS generations;
DROP TABLE IF EXISTS nfts;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;


-- MySQL dump 10.13  Distrib 8.0.39, for Win64 (x86_64)
-- Host: localhost    Database: aigc
-- Server version 8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;



-- ============================
-- Table structure for `users`
-- ============================

/*!40101 SET @saved_cs_client     = @@character_set_client */;
 /*!50503 SET character_set_client = utf8mb4 */;

CREATE TABLE `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '用户唯一ID',
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户登录名',
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户邮箱',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '哈希加盐后的密码',
  `role` enum('user','admin') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'user',
  `status` enum('active','banned') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

 /*!40101 SET character_set_client = @saved_cs_client */;


-- ============================
-- Table structure for `generations`
-- ============================

/*!40101 SET @saved_cs_client     = @@character_set_client */;
 /*!50503 SET character_set_client = utf8mb4 */;

CREATE TABLE `generations` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `uuid` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint unsigned NOT NULL,
  `status` enum('queued','processing','completed','failed') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'queued',
  `generation_type` enum('t2i','i2i','t2v','i2v') COLLATE utf8mb4_unicode_ci NOT NULL,
  `prompt` text COLLATE utf8mb4_unicode_ci,
  `parameters` json DEFAULT NULL,
  `result_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `physical_path` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_uuid` (`uuid`),
  KEY `idx_user_status` (`user_id`,`status`),
  CONSTRAINT `fk_generations_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



-- ============================
-- Table structure for `collections`
-- ============================


/*!40101 SET @saved_cs_client     = @@character_set_client */;
 /*!50503 SET character_set_client = utf8mb4 */;

CREATE TABLE `collections` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint unsigned NOT NULL,
  `parent_id` bigint unsigned DEFAULT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `node_type` enum('folder','file') COLLATE utf8mb4_unicode_ci NOT NULL,
  `generation_id` bigint unsigned DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_parent` (`user_id`,`parent_id`),
  KEY `fk_collections_parent_id` (`parent_id`),
  KEY `fk_collections_generation_id` (`generation_id`),
  CONSTRAINT `fk_collections_generation_id` FOREIGN KEY (`generation_id`) REFERENCES `generations` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_collections_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `collections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_collections_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================
-- Table structure for `nfts`
-- ============================


/*!40101 SET @saved_cs_client     = @@character_set_client */;
 /*!50503 SET character_set_client = utf8mb4 */;

CREATE TABLE `nfts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `generation_id` bigint unsigned NOT NULL,
  `owner_user_id` bigint unsigned NOT NULL,
  `token_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_address` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `transaction_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` enum('pending','confirmed','failed') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confirmed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_generation_id` (`generation_id`),
  UNIQUE KEY `uk_transaction_hash` (`transaction_hash`),
  KEY `fk_nfts_owner_user_id` (`owner_user_id`),
  CONSTRAINT `fk_nfts_generation_id` FOREIGN KEY (`generation_id`) REFERENCES `generations` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_nfts_owner_user_id` FOREIGN KEY (`owner_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =====================================================
-- Trigger: Auto-create root collection on user insertion
-- =====================================================

DROP TRIGGER IF EXISTS trg_create_root_collection;

DELIMITER //

CREATE TRIGGER trg_create_root_collection
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO collections (user_id, parent_id, name, node_type, generation_id)
    VALUES (NEW.id, NULL, '/', 'folder', NULL);
END //

DELIMITER ;
