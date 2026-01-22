-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Creation time: Dec 20, 2025 at 09:23
-- Server version: 10.11.11-MariaDB
-- PHP-Version: 8.2.28

-- ========================================
-- FINIA Database Schema
-- Version: 1.0
-- Purpose: Complete database initialization
-- ========================================

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

-- ========================================
-- DATABASE TABLES
-- ========================================

--
-- Table structure for table `tbl_account`
--

CREATE TABLE `tbl_account` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `name` varchar(128) NOT NULL,
  `iban_accountNumber` varchar(32) NOT NULL,
  `bic_market` text NOT NULL,
  `startAmount` decimal(20,10) NOT NULL,
  `dateStart` datetime NOT NULL,
  `dateEnd` datetime DEFAULT NULL,
  `type` bigint(20) NOT NULL,
  `clearingAccount` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_accountImportFormat`
--

CREATE TABLE `tbl_accountImportFormat` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `type` varchar(128) NOT NULL,
  `fileEnding` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_accountImportPath`
--

CREATE TABLE `tbl_accountImportPath` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `path` varchar(256) NOT NULL,
  `account` bigint(20) NOT NULL,
  `importFormat` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_accountingEntry`
--

CREATE TABLE `tbl_accountingEntry` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `dateImport` datetime NOT NULL,
  `checked` tinyint(4) NOT NULL DEFAULT 0,
  `amount` decimal(20,10) NOT NULL,
  `transaction` bigint(20) NOT NULL,
  `accountingPlanned` bigint(20) DEFAULT NULL,
  `category` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_accountReserve`
--

CREATE TABLE `tbl_accountReserve` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `amount` decimal(20,10) NOT NULL,
  `dateSet` datetime NOT NULL,
  `account` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_accountType`
--

CREATE TABLE `tbl_accountType` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `type` varchar(128) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_category`
--

CREATE TABLE `tbl_category` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `name` varchar(128) NOT NULL,
  `category` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_categoryAutomation`
--

CREATE TABLE `tbl_categoryAutomation` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `columnName` text NOT NULL,
  `rule` varchar(400) NOT NULL,
  `category` bigint(20) NOT NULL,
  `account` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_loan`
--

CREATE TABLE `tbl_loan` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `intrestRate` decimal(20,10) DEFAULT NULL,
  `account` bigint(20) NOT NULL,
  `categoryRebooking` bigint(20) DEFAULT NULL,
  `categoryIntrest` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

-- --------------------------------------------------------

--
-- Table structure for table `tbl_planning`
--

CREATE TABLE `tbl_planning` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `description` text DEFAULT NULL,
  `amount` decimal(20,10) NOT NULL,
  `dateStart` datetime NOT NULL,
  `dateEnd` datetime DEFAULT NULL,
  `account` bigint(20) NOT NULL,
  `category` bigint(20) NOT NULL,
  `cycle` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_planningCycle`
--

CREATE TABLE `tbl_planningCycle` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `cycle` varchar(128) NOT NULL,
  `periodValue` decimal(10,2) NOT NULL DEFAULT 1.00,
  `periodUnit` char(1) NOT NULL DEFAULT 'm' -- d=Tag, m=Monat, y=Jahr
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_planningEntry`
--

CREATE TABLE `tbl_planningEntry` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `dateValue` datetime NOT NULL,
  `planning` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_share`
--

CREATE TABLE `tbl_share` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `name` text DEFAULT NULL,
  `isin` varchar(12) NOT NULL,
  `wkn` varchar(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_shareHistory`
--

CREATE TABLE `tbl_shareHistory` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `amount` decimal(20,10) NOT NULL,
  `date` datetime NOT NULL,
  `checked` tinyint(4) NOT NULL DEFAULT 0,
  `share` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_shareTransaction`
--

CREATE TABLE `tbl_shareTransaction` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `tradingVolume` decimal(20,10) NOT NULL,
  `dateTransaction` datetime NOT NULL,
  `checked` tinyint(4) NOT NULL DEFAULT 0,
  `share` bigint(20) NOT NULL,
  `accountingEntry` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_transaction`
--

CREATE TABLE `tbl_transaction` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `dateImport` datetime NOT NULL,
  `iban` varchar(32) DEFAULT NULL,
  `bic` text DEFAULT NULL,
  `description` varchar(378) NOT NULL,
  `amount` decimal(20,10) NOT NULL,
  `dateValue` datetime NOT NULL,
  `recipientApplicant` text DEFAULT NULL,
  `account` bigint(20) NOT NULL,
  `duplicateHashComputed` varchar(32) GENERATED ALWAYS AS (MD5(CONCAT(COALESCE(`iban`,''),'|',`description`,'|',CAST(`amount` AS CHAR),'|',CAST(`dateValue` AS CHAR),'|',CAST(`account` AS CHAR)))) VIRTUAL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- ========================================
-- DATABASE INDEXES
-- ========================================

--
-- Indexes for table `tbl_account`
--
ALTER TABLE `tbl_account`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`),
  ADD UNIQUE KEY `iban_accountNumber` (`iban_accountNumber`),
  ADD KEY `tbl_account_idx_tbl_accountType_type` (`type`),
  ADD KEY `tbl_account_idx_tbl_account_clearingAccount` (`clearingAccount`);

--
-- Indexes for table `tbl_accountImportFormat`
--
ALTER TABLE `tbl_accountImportFormat`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `type` (`type`);

--
-- Indexes for table `tbl_accountImportPath`
--
ALTER TABLE `tbl_accountImportPath`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `path` (`path`),
  ADD KEY `tbl_accountImportPath_idx_tbl_account_account` (`account`),
  ADD KEY `tbl_accountImportPath_idx_tbl_accountImportFormat_importFormat` (`importFormat`);

--
-- Indexes for table `tbl_accountingEntry`
--
ALTER TABLE `tbl_accountingEntry`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_accountingEntry_idx_tbl_transaction_transaction` (`transaction`),
  ADD KEY `tbl_accountingEntry_idx_tbl_planning_accountingPlanned` (`accountingPlanned`),
  ADD KEY `tbl_accountingEntry_idx_tbl_category_category` (`category`);

--
-- Indexes for table `tbl_accountReserve`
--
ALTER TABLE `tbl_accountReserve`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_accountReserve_idx_tbl_account_account` (`account`);

--
-- Indexes for table `tbl_accountType`
--
ALTER TABLE `tbl_accountType`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `type` (`type`);

--
-- Indexes for table `tbl_category`
--
ALTER TABLE `tbl_category`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`),
  ADD KEY `tbl_category_idx_tbl_category_category` (`category`);

--
-- Indexes for table `tbl_categoryAutomation`
--
ALTER TABLE `tbl_categoryAutomation`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `duplicateHash` (`rule`,`account`,`category`),
  ADD KEY `tbl_categoryAutomation_idx_tbl_category_category` (`category`),
  ADD KEY `tbl_categoryAutomation_idx_tbl_account_account` (`account`);

--
-- Indexes for table `tbl_loan`
--
ALTER TABLE `tbl_loan`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_loan_idx_tbl_account_account` (`account`),
  ADD KEY `tbl_loan_idx_tbl_category_categoryRebooking` (`categoryRebooking`),
  ADD KEY `tbl_loan_idx_tbl_category_categoryIntrest` (`categoryIntrest`);

--
-- Indexes for table `tbl_planning`
--
ALTER TABLE `tbl_planning`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `duplicateHash` (`account`,`category`,`cycle`,`dateStart`,`amount`),
  ADD KEY `tbl_planning_idx_tbl_category_category` (`category`),
  ADD KEY `tbl_planning_idx_tbl_planningCycle_cycle` (`cycle`);

--
-- Indexes for table `tbl_planningCycle`
--
ALTER TABLE `tbl_planningCycle`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `cycle` (`cycle`);

--
-- Indexes for table `tbl_planningEntry`
--
ALTER TABLE `tbl_planningEntry`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_planningEntry_idx_tbl_planning_planning` (`planning`);

--
-- Indexes for table `tbl_share`
--
ALTER TABLE `tbl_share`
  ADD PRIMARY KEY (`id`),
  ADD INDEX `idx_isin` (`isin`),
  ADD UNIQUE KEY `unique_isin` (`isin`),
  ADD UNIQUE KEY `wkn` (`wkn`);

--
-- Indexes for table `tbl_shareHistory`
--
ALTER TABLE `tbl_shareHistory`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_shareHistory_idx_tbl_share_share` (`share`),
  ADD UNIQUE KEY `tbl_shareHistory_unique_share_date` (`share`,`date`);

--
-- Indexes for table `tbl_shareTransaction`
--
ALTER TABLE `tbl_shareTransaction`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_share_transaction_unique` (`share`, `tradingVolume`, `dateTransaction`),
  ADD KEY `tbl_shareTransaction_idx_tbl_share_share` (`share`),
  ADD KEY `tbl_shareTransaction_idx_tbl_accountingEntry_accountingEntry` (`accountingEntry`);

--
-- Indexes for table `tbl_transaction`
--
ALTER TABLE `tbl_transaction`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `duplicateHash` (`duplicateHashComputed`),
  ADD KEY `tbl_transaction_idx_tbl_account_account` (`account`);

-- ========================================
-- AUTO_INCREMENT CONFIGURATION
-- ========================================

--
-- AUTO_INCREMENT for table `tbl_account`
--
ALTER TABLE `tbl_account`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_accountImportFormat`
--
ALTER TABLE `tbl_accountImportFormat`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_accountImportPath`
--
ALTER TABLE `tbl_accountImportPath`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_accountingEntry`
--
ALTER TABLE `tbl_accountingEntry`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_accountReserve`
--
ALTER TABLE `tbl_accountReserve`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_accountType`
--
ALTER TABLE `tbl_accountType`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_category`
--
ALTER TABLE `tbl_category`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_categoryAutomation`
--
ALTER TABLE `tbl_categoryAutomation`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_loan`
--
ALTER TABLE `tbl_loan`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_planning`
--
ALTER TABLE `tbl_planning`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_planningCycle`
--
ALTER TABLE `tbl_planningCycle`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_planningEntry`
--
ALTER TABLE `tbl_planningEntry`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_share`
--
ALTER TABLE `tbl_share`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_shareHistory`
--
ALTER TABLE `tbl_shareHistory`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_shareTransaction`
--
ALTER TABLE `tbl_shareTransaction`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tbl_transaction`
--
ALTER TABLE `tbl_transaction`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

-- ========================================
-- DATABASE VIEWS
-- ========================================

-- View: Accounting entries not yet checked
--

CREATE VIEW `view_accountingEntriesNotChecked` AS SELECT `tbl_transaction`.`account` AS `account`, `tbl_transaction`.`description` AS `description`, `tbl_transaction`.`id` AS `transactionId` FROM (`tbl_transaction` left join `tbl_accountingEntry` on(`tbl_accountingEntry`.`transaction` = `tbl_transaction`.`id`)) WHERE `tbl_accountingEntry`.`checked` = 0 GROUP BY `tbl_transaction`.`id` ;

-- View: Planning balances aggregated by category and month
--
CREATE VIEW `view_balancesPlanning` AS SELECT sum(`tbl_planning`.`amount`) AS `amountSum`, `tbl_planning`.`category` AS `categoryID`, `tbl_planning`.`account` AS `accountID`, `tbl_planningEntry`.`dateValue` AS `dateValue`, `tbl_category`.`name` AS `categoryName` FROM ((`tbl_planningEntry` left join `tbl_planning` on(`tbl_planningEntry`.`planning` = `tbl_planning`.`id`)) left join `tbl_category` on(`tbl_planning`.`category` = `tbl_category`.`id`)) GROUP BY `tbl_category`.`name`, `tbl_planning`.`account`, year(`tbl_planningEntry`.`dateValue`), month(`tbl_planningEntry`.`dateValue`) ;

-- View: Share portfolio values (current holdings with market value)
-- Calculates: currentVolume = sum of all transactions, currentPrice = latest history, portfolioValue = volume × price
--
CREATE VIEW `view_sharePortfolioValue` AS
SELECT
  s.id,
  s.name,
  s.isin,
  s.wkn,
  COALESCE(SUM(t.tradingVolume), 0) AS currentVolume,
  COALESCE(latest_history.amount, 0) AS currentPrice,
  COALESCE(SUM(t.tradingVolume), 0) * COALESCE(latest_history.amount, 0) AS portfolioValue
FROM tbl_share s
LEFT JOIN tbl_shareTransaction t ON t.share = s.id
LEFT JOIN (
  SELECT h.share, h.amount, h.date
  FROM tbl_shareHistory h
  INNER JOIN (
    SELECT share, MAX(date) AS latest_date
    FROM tbl_shareHistory
    GROUP BY share
  ) latest ON h.share = latest.share AND h.date = latest.latest_date
) latest_history ON s.id = latest_history.share
GROUP BY s.id, s.name, s.isin, s.wkn, latest_history.amount;

-- View: Monthly snapshot of portfolio values at month-end
-- Uses latest price per month and cumulative transactions up to month-end
--
CREATE VIEW `view_shareMonthlySnapshot` AS
WITH RECURSIVE months AS (
  -- Start at the earliest history month-end
  SELECT LAST_DAY(MIN(date)) AS month_end_date
  FROM tbl_shareHistory
  WHERE amount IS NOT NULL
  UNION ALL
  -- Generate month-ends up to one year in die Zukunft
  SELECT LAST_DAY(month_end_date + INTERVAL 1 MONTH)
  FROM months
  WHERE month_end_date < LAST_DAY(CURRENT_DATE + INTERVAL 1 YEAR)
),
shares_with_history AS (
  SELECT DISTINCT share
  FROM tbl_shareHistory
  WHERE amount IS NOT NULL
),
month_ends AS (
  -- Cross join: alle relevanten Wertpapiere × alle Monatsenden
  SELECT s.share, m.month_end_date
  FROM shares_with_history s
  CROSS JOIN months m
),
latest_prices AS (
  -- Für jeden Monat eines Wertpapiers: letzter Preis vor/zu Monatsende
  SELECT
    me.share,
    me.month_end_date,
    MAX(sh.date) AS latest_price_date
  FROM month_ends me
  INNER JOIN tbl_shareHistory sh ON sh.share = me.share
    AND sh.amount IS NOT NULL
    AND DATE(sh.date) <= DATE(me.month_end_date)
  GROUP BY me.share, me.month_end_date
)
SELECT
  h.share AS share_id,
  s.name AS share_name,
  lp.month_end_date,
  h.amount AS price,
  COALESCE(SUM(t.tradingVolume), 0) AS volume,
  h.amount * COALESCE(SUM(t.tradingVolume), 0) AS portfolio_value
FROM latest_prices lp
INNER JOIN tbl_shareHistory h ON h.share = lp.share
  AND DATE(h.date) = DATE(lp.latest_price_date)
  AND h.amount IS NOT NULL
INNER JOIN tbl_share s ON s.id = h.share
LEFT JOIN tbl_shareTransaction t ON t.share = h.share
  AND DATE(t.dateTransaction) <= DATE(lp.month_end_date)
GROUP BY h.share, s.name, lp.month_end_date, h.amount;

-- View: Full hierarchical category names (parent - child - grandchild structure)
--
CREATE VIEW `view_categoryFullname` AS WITH RECURSIVE Qry(`id`, `fullname`, `pID`) AS (SELECT `tbl_category`.`id` AS `id`, `tbl_category`.`name` AS `fullname`, `tbl_category`.`category` AS `pID` FROM `tbl_category` UNION SELECT `Qry`.`id` AS `id`, concat(`tbl_category`.`name`,' - ',`Qry`.`fullname`) AS `CONCAT(tbl_category.name, ' - ', Qry.fullname)`, `tbl_category`.`category` AS `category` FROM (`Qry` join `tbl_category` on(`Qry`.`pID` = `tbl_category`.`id`))) SELECT `Qry`.`id` AS `id`, `tbl_category`.`name` AS `name`, `Qry`.`fullname` AS `fullname` FROM (`tbl_category` left join `Qry` on(`Qry`.`id` = `tbl_category`.`id`)) WHERE `Qry`.`pID` is null GROUP BY `Qry`.`fullname`  ;

-- View: Monthly account reserves (tracks reserve amount for each month)
--
CREATE VIEW `view_reserveMonthly` AS WITH RECURSIVE dateList AS (SELECT str_to_date(concat(year(min(`tbl_transaction`.`dateValue`)),'-01-01'),'%Y-%m-%d') AS `date` FROM `tbl_transaction` UNION ALL SELECT `dateList`.`date`+ interval 1 month AS `date + INTERVAL 1 month` FROM `dateList` WHERE `dateList`.`date` < current_timestamp() + interval 1 year)  SELECT `tbl_accountReserve`.`account` AS `account`, `dateList`.`date` AS `dateSet`, `tbl_accountReserve`.`amount` AS `amount` FROM ((`dateList` left join `tbl_accountReserve` on(`tbl_accountReserve`.`dateSet` < `dateList`.`date`)) left join (select `tbl_accountReserve`.`id` AS `id`,`tbl_accountReserve`.`dateImport` AS `dateImport`,`tbl_accountReserve`.`amount` AS `amount`,`tbl_accountReserve`.`dateSet` AS `dateSet`,`tbl_accountReserve`.`account` AS `account` from `tbl_accountReserve`) `t2` on(`tbl_accountReserve`.`dateSet` < `t2`.`dateSet` and `tbl_accountReserve`.`account` = `t2`.`account` and `t2`.`dateSet` < `dateList`.`date`)) WHERE `tbl_accountReserve`.`amount` is not null AND `t2`.`id` is null ORDER BY `tbl_accountReserve`.`account` ASC, `dateList`.`date` ASC;

-- View: Transactions without accounting entries (unprocessed transactions)
--
CREATE VIEW `view_transactionsWithoutAccountingEntry` AS SELECT `tbl_transaction`.`account` AS `account`, `tbl_transaction`.`description` AS `description`, `tbl_transaction`.`id` AS `transactionId` FROM `tbl_transaction` WHERE !(`tbl_transaction`.`id` in (select `tbl_accountingEntry`.`transaction` from `tbl_accountingEntry`)) ;

-- View: Transactions without category assignment (uncategorized transactions)
--
CREATE VIEW `view_transactionsWithoutCategory` AS SELECT `tbl_transaction`.`account` AS `account`, `tbl_transaction`.`description` AS `description`, `tbl_transaction`.`id` AS `transactionId` FROM (`tbl_transaction` left join `tbl_accountingEntry` on(`tbl_accountingEntry`.`transaction` = `tbl_transaction`.`id`)) WHERE `tbl_accountingEntry`.`category` is null GROUP BY `tbl_transaction`.`id` ;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `tbl_account`
--
ALTER TABLE `tbl_account`
  ADD CONSTRAINT `tbl_account_idx_tbl_accountType_type` FOREIGN KEY (`type`) REFERENCES `tbl_accountType` (`id`),
  ADD CONSTRAINT `tbl_account_idx_tbl_account_clearingAccount` FOREIGN KEY (`clearingAccount`) REFERENCES `tbl_account` (`id`);

--
-- Constraints for table `tbl_accountImportPath`
--
ALTER TABLE `tbl_accountImportPath`
  ADD CONSTRAINT `tbl_accountImportPath_idx_tbl_accountImportFormat_importFormat` FOREIGN KEY (`importFormat`) REFERENCES `tbl_accountImportFormat` (`id`),
  ADD CONSTRAINT `tbl_accountImportPath_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`);

--
-- Constraints for table `tbl_accountingEntry`
--
ALTER TABLE `tbl_accountingEntry`
  ADD CONSTRAINT `tbl_accountingEntry_idx_tbl_category_category` FOREIGN KEY (`category`) REFERENCES `tbl_category` (`id`),
  ADD CONSTRAINT `tbl_accountingEntry_idx_tbl_planning_accountingPlanned` FOREIGN KEY (`accountingPlanned`) REFERENCES `tbl_planning` (`id`),
  ADD CONSTRAINT `tbl_accountingEntry_idx_tbl_transaction_transaction` FOREIGN KEY (`transaction`) REFERENCES `tbl_transaction` (`id`);

--
-- Constraints for table `tbl_accountReserve`
--
ALTER TABLE `tbl_accountReserve`
  ADD CONSTRAINT `tbl_accountReserve_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`);

--
-- Constraints for table `tbl_category`
--
ALTER TABLE `tbl_category`
  ADD CONSTRAINT `tbl_category_idx_tbl_category_category` FOREIGN KEY (`category`) REFERENCES `tbl_category` (`id`);

--
-- Constraints for table `tbl_categoryAutomation`
--
ALTER TABLE `tbl_categoryAutomation`
  ADD CONSTRAINT `tbl_categoryAutomation_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`),
  ADD CONSTRAINT `tbl_categoryAutomation_idx_tbl_category_category` FOREIGN KEY (`category`) REFERENCES `tbl_category` (`id`);

--
-- Constraints for table `tbl_loan`
--
ALTER TABLE `tbl_loan`
  ADD CONSTRAINT `tbl_loan_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`),
  ADD CONSTRAINT `tbl_loan_idx_tbl_category_categoryIntrest` FOREIGN KEY (`categoryIntrest`) REFERENCES `tbl_category` (`id`),
  ADD CONSTRAINT `tbl_loan_idx_tbl_category_categoryRebooking` FOREIGN KEY (`categoryRebooking`) REFERENCES `tbl_category` (`id`);

--
-- Constraints for table `tbl_planning`
--
ALTER TABLE `tbl_planning`
  ADD CONSTRAINT `tbl_planning_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`),
  ADD CONSTRAINT `tbl_planning_idx_tbl_category_category` FOREIGN KEY (`category`) REFERENCES `tbl_category` (`id`),
  ADD CONSTRAINT `tbl_planning_idx_tbl_planningCycle_cycle` FOREIGN KEY (`cycle`) REFERENCES `tbl_planningCycle` (`id`);

--
-- Constraints for table `tbl_planningEntry`
--
ALTER TABLE `tbl_planningEntry`
  ADD CONSTRAINT `tbl_planningEntry_idx_tbl_planning_planning` FOREIGN KEY (`planning`) REFERENCES `tbl_planning` (`id`);

--
-- Constraints for table `tbl_shareHistory`
--
ALTER TABLE `tbl_shareHistory`
  ADD CONSTRAINT `tbl_shareHistory_idx_tbl_share_share` FOREIGN KEY (`share`) REFERENCES `tbl_share` (`id`);

--
-- Constraints for table `tbl_shareTransaction`
--
ALTER TABLE `tbl_shareTransaction`
  ADD CONSTRAINT `tbl_shareTransaction_idx_tbl_accountingEntry_accountingEntry` FOREIGN KEY (`accountingEntry`) REFERENCES `tbl_accountingEntry` (`id`),
  ADD CONSTRAINT `tbl_shareTransaction_idx_tbl_share_share` FOREIGN KEY (`share`) REFERENCES `tbl_share` (`id`);

--
-- Constraints for table `tbl_transaction`
--
ALTER TABLE `tbl_transaction`
  ADD CONSTRAINT `tbl_transaction_idx_tbl_account_account` FOREIGN KEY (`account`) REFERENCES `tbl_account` (`id`);

-- ========================================
-- DATA INITIALIZATION & TRIGGERS
-- ========================================
UPDATE `tbl_planningCycle` 
SET `periodValue` = 1.00, `periodUnit` = 'm' 
WHERE LOWER(`cycle`) LIKE '%monat%' OR LOWER(`cycle`) LIKE '%month%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 7.00, `periodUnit` = 'd' 
WHERE LOWER(`cycle`) LIKE '%woche%' OR LOWER(`cycle`) LIKE '%week%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 3.00, `periodUnit` = 'm' 
WHERE LOWER(`cycle`) LIKE '%quart%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 6.00, `periodUnit` = 'm' 
WHERE LOWER(`cycle`) LIKE '%halb%' OR LOWER(`cycle`) LIKE '%semi%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 1.00, `periodUnit` = 'y' 
WHERE LOWER(`cycle`) LIKE '%jahr%' OR LOWER(`cycle`) LIKE '%year%' OR LOWER(`cycle`) LIKE '%jährlich%' OR LOWER(`cycle`) LIKE '%annual%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 1.00, `periodUnit` = 'd' 
WHERE LOWER(`cycle`) LIKE '%tag%' OR LOWER(`cycle`) LIKE '%day%' OR LOWER(`cycle`) LIKE '%täglich%' OR LOWER(`cycle`) LIKE '%daily%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 0.00, `periodUnit` = 'd' 
WHERE LOWER(`cycle`) LIKE '%einmal%' OR LOWER(`cycle`) LIKE '%once%' OR LOWER(`cycle`) LIKE '%single%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 14.00, `periodUnit` = 'd' 
WHERE LOWER(`cycle`) LIKE '%zweiwoche%' OR LOWER(`cycle`) LIKE '%biweek%' OR LOWER(`cycle`) LIKE '%14-t%';

UPDATE `tbl_planningCycle` 
SET `periodValue` = 2.00, `periodUnit` = 'm' 
WHERE LOWER(`cycle`) LIKE '%zwei-monat%' OR LOWER(`cycle`) LIKE '%bimonth%';

-- ========================================
-- PERFORMANCE INDEXES
-- ========================================

--
-- Composite and performance indexes for common queries
--
CREATE INDEX IF NOT EXISTS `idx_planning_dateStart` ON `tbl_planning` (`dateStart`);
CREATE INDEX IF NOT EXISTS `idx_planning_account` ON `tbl_planning` (`account`);
CREATE INDEX IF NOT EXISTS `idx_planning_category` ON `tbl_planning` (`category`);
CREATE INDEX IF NOT EXISTS `idx_planning_cycle` ON `tbl_planning` (`cycle`);
CREATE INDEX IF NOT EXISTS `idx_planning_account_dateStart` ON `tbl_planning` (`account`, `dateStart`);

-- Planning entry indexes
CREATE INDEX IF NOT EXISTS `idx_planningEntry_planning` ON `tbl_planningEntry` (`planning`);
CREATE INDEX IF NOT EXISTS `idx_planningEntry_dateValue` ON `tbl_planningEntry` (`dateValue`);

-- Transaction indexes
CREATE INDEX IF NOT EXISTS `idx_transaction_account` ON `tbl_transaction` (`account`);
CREATE INDEX IF NOT EXISTS `idx_transaction_dateValue` ON `tbl_transaction` (`dateValue`);
CREATE INDEX IF NOT EXISTS `idx_transaction_amount` ON `tbl_transaction` (`amount`);

-- Accounting entry indexes
CREATE INDEX IF NOT EXISTS `idx_accountingEntry_transaction` ON `tbl_accountingEntry` (`transaction`);
CREATE INDEX IF NOT EXISTS `idx_accountingEntry_checked` ON `tbl_accountingEntry` (`checked`);
CREATE INDEX IF NOT EXISTS `idx_accountingEntry_category` ON `tbl_accountingEntry` (`category`);

-- Account indexes
CREATE INDEX IF NOT EXISTS `idx_account_type` ON `tbl_account` (`type`);
CREATE INDEX IF NOT EXISTS `idx_account_name` ON `tbl_account` (`name`);

-- Share indexes
CREATE INDEX IF NOT EXISTS `idx_share_isin` ON `tbl_share` (`isin`);

-- ========================================
-- AUTO-TRIGGERS
-- ========================================

--
-- Table: tbl_setting (global and user-specific settings)
--
CREATE TABLE IF NOT EXISTS `tbl_setting` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NULL,
  `key` VARCHAR(100) NOT NULL,
  `value` JSON NOT NULL,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_user_key_lookup` (`user_id`, `key`)
);


--
-- Trigger: Auto-create accounting entry for each transaction
-- Ensures every transaction has an associated accounting entry with initial state checked=0
--
DELIMITER $$
CREATE TRIGGER `trg_transaction_create_accounting_entry`
AFTER INSERT ON `tbl_transaction`
FOR EACH ROW
BEGIN
  INSERT INTO `tbl_accountingEntry` (
    `dateImport`,
    `checked`,
    `amount`,
    `transaction`,
    `accountingPlanned`,
    `category`
  )
  VALUES (
    NOW(),
    0,
    NEW.`amount`,
    NEW.`id`,
    NULL,
    NULL
  );
END$$
DELIMITER ;

-- ========================================
-- DATABASE INITIALIZATION COMPLETE
-- ========================================
-- All tables, indexes, views, constraints, and triggers created successfully.
-- Ready for application usage.

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
