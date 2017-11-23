SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";

CREATE TABLE `nagios_alerts` (
  `date_inserted` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `date_sent` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `message_text` text NOT NULL,
  `status` enum('UNSENT','SENT','ERROR') NOT NULL,
  `hostname` varchar(100) NOT NULL,
  `service_name` varchar(100) NOT NULL,
  `notification_type` varchar(20) NOT NULL,
  `id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


ALTER TABLE `nagios_alerts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `status` (`status`);
