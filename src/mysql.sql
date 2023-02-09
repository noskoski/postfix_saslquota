
CREATE TABLE `log` ( `sasl_username` VARCHAR(320) NOT NULL , `date` DATETIME(6) NOT NULL , PRIMARY KEY (`sasl_username`, `date`)) ENGINE = InnoDB;