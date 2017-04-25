-- phpMyAdmin SQL Dump
-- version 4.2.12deb2+deb8u2
-- http://www.phpmyadmin.net
--
-- Generation Time: Apr 24, 2017 at 09:56 PM
-- Server version: 5.5.54-0+deb8u1
-- PHP Version: 5.6.30-0+deb8u1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `telegram_bot`
--

-- --------------------------------------------------------

--
-- Table structure for table `nagios_alerts`
--

CREATE TABLE IF NOT EXISTS `nagios_alerts` (
  `date_inserted` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `date_sent` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `message_text` text NOT NULL,
  `status` enum('UNSENT','SENT','ERROR') NOT NULL,
  `hostname` varchar(100) NOT NULL,
  `service_name` varchar(100) NOT NULL,
  `notification_type` varchar(20) NOT NULL,
`id` bigint(20) NOT NULL
) ENGINE=InnoDB AUTO_INCREMENT=657 DEFAULT CHARSET=latin1;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `nagios_alerts`
--
ALTER TABLE `nagios_alerts`
 ADD PRIMARY KEY (`id`), ADD KEY `status` (`status`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `nagios_alerts`
--
ALTER TABLE `nagios_alerts`
MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=657;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
