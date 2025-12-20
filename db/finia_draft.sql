-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Creation time: Dec 20, 2025 at 09:23
-- Server version: 10.11.11-MariaDB
-- PHP-Version: 8.2.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `FiniA`
--

-- --------------------------------------------------------

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
  `id` bigint(20) NOT NULL,
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

--
-- Table structure for table `tbl_loanSumExclude`
--

CREATE TABLE `tbl_loanSumExclude` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `loanId` bigint(20) NOT NULL,
  `category` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

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
  `cycle` varchar(128) NOT NULL
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
  `wkn` varchar(6) NOT NULL
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
  `accountingEntry` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tbl_transaction`
--

CREATE TABLE `tbl_transaction` (
  `id` bigint(20) NOT NULL,
  `dateImport` datetime NOT NULL,
  `iban` varchar(32) DEFAULT NULL,
  `bic` text DEFAULT NULL,
  `description` varchar(378) NOT NULL,
  `amount` decimal(20,10) NOT NULL,
  `dateValue` datetime NOT NULL,
  `recipientApplicant` text DEFAULT NULL,
  `account` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci;

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_accountingEntriesNotChecked`
-- (See below for the actual view)
--
CREATE TABLE `view_accountingEntriesNotChecked` (
`account` bigint(20)
,`description` varchar(378)
,`transactionId` bigint(20)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_balances`
-- (See below for the actual view)
--
CREATE TABLE `view_balances` (
`amountSum` decimal(42,10)
,`categoryID` bigint(20)
,`accountID` bigint(20)
,`dateValue` datetime /* mariadb-5.3 */
,`categoryName` varchar(128)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_balancesPlanning`
-- (See below for the actual view)
--
CREATE TABLE `view_balancesPlanning` (
`amountSum` decimal(42,10)
,`categoryID` bigint(20)
,`accountID` bigint(20)
,`dateValue` datetime
,`categoryName` varchar(128)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_balancesTransactions`
-- (See below for the actual view)
--
CREATE TABLE `view_balancesTransactions` (
`amountSum` decimal(42,10)
,`categoryID` bigint(20)
,`accountID` bigint(20)
,`dateValue` datetime
,`categoryName` varchar(128)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_categoryFullname`
-- (See below for the actual view)
--
CREATE TABLE `view_categoryFullname` (
`id` bigint(20)
,`name` varchar(128)
,`fullname` varchar(128)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_reserveMonthly`
-- (See below for the actual view)
--
CREATE TABLE `view_reserveMonthly` (
`account` bigint(20)
,`dateSet` date
,`amount` decimal(20,10)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_transactionsWithoutAccountingEntry`
-- (See below for the actual view)
--
CREATE TABLE `view_transactionsWithoutAccountingEntry` (
`account` bigint(20)
,`description` varchar(378)
,`transactionId` bigint(20)
);

-- --------------------------------------------------------

--
-- Placeholder structure for view `view_transactionsWithoutCategory`
-- (See below for the actual view)
--
CREATE TABLE `view_transactionsWithoutCategory` (
`account` bigint(20)
,`description` varchar(378)
,`transactionId` bigint(20)
);

--
-- Indexes for dumped tables
--

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
-- Indexes for table `tbl_loanSumExclude`
--
ALTER TABLE `tbl_loanSumExclude`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_loanSumExclude_idx_tbl_loan_loanId` (`loanId`),
  ADD KEY `tbl_loanSumExclude_idx_tbl_category_category` (`category`);

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
  ADD UNIQUE KEY `isin` (`isin`),
  ADD UNIQUE KEY `wkn` (`wkn`);

--
-- Indexes for table `tbl_shareHistory`
--
ALTER TABLE `tbl_shareHistory`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_shareHistory_idx_tbl_share_share` (`share`);

--
-- Indexes for table `tbl_shareTransaction`
--
ALTER TABLE `tbl_shareTransaction`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tbl_shareTransaction_idx_tbl_share_share` (`share`),
  ADD KEY `tbl_shareTransaction_idx_tbl_accountingEntry_accountingEntry` (`accountingEntry`);

--
-- Indexes for table `tbl_transaction`
--
ALTER TABLE `tbl_transaction`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `duplicateHash` (`iban`,`description`,`amount`,`dateValue`,`account`),
  ADD KEY `tbl_transaction_idx_tbl_account_account` (`account`);

--
-- AUTO_INCREMENT for dumped tables
--

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
-- AUTO_INCREMENT for table `tbl_loanSumExclude`
--
ALTER TABLE `tbl_loanSumExclude`
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

-- --------------------------------------------------------

--
-- Structure for view `view_accountingEntriesNotChecked`
--
DROP TABLE IF EXISTS `view_accountingEntriesNotChecked`;

CREATE VIEW `view_accountingEntriesNotChecked` AS SELECT `tbl_transaction`.`account` AS `account`, `tbl_transaction`.`description` AS `description`, `tbl_transaction`.`id` AS `transactionId` FROM (`tbl_transaction` left join `tbl_accountingEntry` on(`tbl_accountingEntry`.`transaction` = `tbl_transaction`.`id`)) WHERE `tbl_accountingEntry`.`checked` = 0 GROUP BY `tbl_transaction`.`id` ;

-- --------------------------------------------------------

--
-- Structure for view `view_balances`
--
DROP TABLE IF EXISTS `view_balances`;

CREATE VIEW `view_balances` AS WITH qry AS (SELECT `view_balancesPlanning`.`amountSum` AS `amountSum`, `view_balancesPlanning`.`categoryID` AS `categoryID`, `view_balancesPlanning`.`accountID` AS `accountID`, `view_balancesPlanning`.`dateValue` AS `dateValue`, `view_balancesPlanning`.`categoryName` AS `categoryName` FROM `view_balancesPlanning` WHERE `view_balancesPlanning`.`dateValue` > current_timestamp() UNION ALL SELECT `view_balancesTransactions`.`amountSum` AS `amountSum`, `view_balancesTransactions`.`categoryID` AS `categoryID`, `view_balancesTransactions`.`accountID` AS `accountID`, `view_balancesTransactions`.`dateValue` AS `dateValue`, `view_balancesTransactions`.`categoryName` AS `categoryName` FROM `view_balancesTransactions`) SELECT `qry`.`amountSum` AS `amountSum`, `qry`.`categoryID` AS `categoryID`, `qry`.`accountID` AS `accountID`, `qry`.`dateValue` AS `dateValue`, `qry`.`categoryName` AS `categoryName` FROM `qry`  ;

-- --------------------------------------------------------

--
-- Structure for view `view_balancesPlanning`
--
DROP TABLE IF EXISTS `view_balancesPlanning`;

CREATE VIEW `view_balancesPlanning` AS SELECT sum(`tbl_planning`.`amount`) AS `amountSum`, `tbl_planning`.`category` AS `categoryID`, `tbl_planning`.`account` AS `accountID`, `tbl_planningEntry`.`dateValue` AS `dateValue`, `tbl_category`.`name` AS `categoryName` FROM ((`tbl_planningEntry` left join `tbl_planning` on(`tbl_planningEntry`.`planning` = `tbl_planning`.`id`)) left join `tbl_category` on(`tbl_planning`.`category` = `tbl_category`.`id`)) GROUP BY `tbl_category`.`name`, `tbl_planning`.`account`, year(`tbl_planningEntry`.`dateValue`), month(`tbl_planningEntry`.`dateValue`) ;

-- --------------------------------------------------------

--
-- Structure for view `view_balancesTransactions`
--
DROP TABLE IF EXISTS `view_balancesTransactions`;

CREATE VIEW `view_balancesTransactions` AS SELECT sum(`tbl_accountingEntry`.`amount`) AS `amountSum`, `tbl_accountingEntry`.`category` AS `categoryID`, `tbl_transaction`.`account` AS `accountID`, `tbl_transaction`.`dateValue` AS `dateValue`, `tbl_category`.`name` AS `categoryName` FROM ((`tbl_accountingEntry` left join `tbl_category` on(`tbl_accountingEntry`.`category` = `tbl_category`.`id`)) left join `tbl_transaction` on(`tbl_accountingEntry`.`transaction` = `tbl_transaction`.`id`)) GROUP BY `tbl_category`.`name`, `tbl_transaction`.`account`, year(`tbl_transaction`.`dateValue`), month(`tbl_transaction`.`dateValue`) ;

-- --------------------------------------------------------

--
-- Structure for view `view_categoryFullname`
--
DROP TABLE IF EXISTS `view_categoryFullname`;

CREATE VIEW `view_categoryFullname` AS WITH RECURSIVE Qry(`id`, `fullname`, `pID`) AS (SELECT `tbl_category`.`id` AS `id`, `tbl_category`.`name` AS `fullname`, `tbl_category`.`category` AS `pID` FROM `tbl_category` UNION SELECT `Qry`.`id` AS `id`, concat(`tbl_category`.`name`,' - ',`Qry`.`fullname`) AS `CONCAT(tbl_category.name, ' - ', Qry.fullname)`, `tbl_category`.`category` AS `category` FROM (`Qry` join `tbl_category` on(`Qry`.`pID` = `tbl_category`.`id`))) SELECT `Qry`.`id` AS `id`, `tbl_category`.`name` AS `name`, `Qry`.`fullname` AS `fullname` FROM (`tbl_category` left join `Qry` on(`Qry`.`id` = `tbl_category`.`id`)) WHERE `Qry`.`pID` is null GROUP BY `Qry`.`fullname`  ;

-- --------------------------------------------------------

--
-- Structure for view `view_reserveMonthly`
--
DROP TABLE IF EXISTS `view_reserveMonthly`;

CREATE VIEW `view_reserveMonthly` AS WITH RECURSIVE dateList AS (SELECT str_to_date(concat(year(min(`tbl_transaction`.`dateValue`)),'-01-01'),'%Y-%m-%d') AS `date` FROM `tbl_transaction` UNION ALL SELECT `dateList`.`date`+ interval 1 month AS `date + INTERVAL 1 month` FROM `dateList` WHERE `dateList`.`date` < current_timestamp() + interval 1 year)  SELECT `tbl_accountReserve`.`account` AS `account`, `dateList`.`date` AS `dateSet`, `tbl_accountReserve`.`amount` AS `amount` FROM ((`dateList` left join `tbl_accountReserve` on(`tbl_accountReserve`.`dateSet` < `dateList`.`date`)) left join (select `tbl_accountReserve`.`id` AS `id`,`tbl_accountReserve`.`dateImport` AS `dateImport`,`tbl_accountReserve`.`amount` AS `amount`,`tbl_accountReserve`.`dateSet` AS `dateSet`,`tbl_accountReserve`.`account` AS `account` from `tbl_accountReserve`) `t2` on(`tbl_accountReserve`.`dateSet` < `t2`.`dateSet` and `tbl_accountReserve`.`account` = `t2`.`account` and `t2`.`dateSet` < `dateList`.`date`)) WHERE `tbl_accountReserve`.`amount` is not null AND `t2`.`id` is null ORDER BY `tbl_accountReserve`.`account` ASC, `dateList`.`date` ASC;

-- --------------------------------------------------------

--
-- Structure for view `view_transactionsWithoutAccountingEntry`
--
DROP TABLE IF EXISTS `view_transactionsWithoutAccountingEntry`;

CREATE VIEW `view_transactionsWithoutAccountingEntry` AS SELECT `tbl_transaction`.`account` AS `account`, `tbl_transaction`.`description` AS `description`, `tbl_transaction`.`id` AS `transactionId` FROM `tbl_transaction` WHERE !(`tbl_transaction`.`id` in (select `tbl_accountingEntry`.`transaction` from `tbl_accountingEntry`)) ;

-- --------------------------------------------------------

--
-- Structure for view `view_transactionsWithoutCategory`
--
DROP TABLE IF EXISTS `view_transactionsWithoutCategory`;

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
-- Constraints for table `tbl_loanSumExclude`
--
ALTER TABLE `tbl_loanSumExclude`
  ADD CONSTRAINT `tbl_loanSumExclude_idx_tbl_category_category` FOREIGN KEY (`category`) REFERENCES `tbl_category` (`id`),
  ADD CONSTRAINT `tbl_loanSumExclude_idx_tbl_loan_loanId` FOREIGN KEY (`loanId`) REFERENCES `tbl_loan` (`id`);

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
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
