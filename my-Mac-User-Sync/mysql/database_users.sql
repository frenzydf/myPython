use db;

CREATE TABLE intune_users(
	userID int not null AUTO_INCREMENT,
	hostname varchar(100) NOT NULL,
	macaddress varchar(17),
	username varchar(100),
	email varchar(100),
	status BOOLEAN DEFAULT TRUE,
	PRIMARY KEY (userID)
);

CREATE TABLE devices(
	deviceID int not null AUTO_INCREMENT,
	macaddr varchar(17) NOT NULL,
	ipaddr varchar(15) NOT NULL,
	hostname varchar(100) NOT NULL,
	lastseen integer(50) NOT NULL,
	PRIMARY KEY (deviceID)
);

CREATE TABLE dhcp_list(
	addrID int not null AUTO_INCREMENT,
	mac varchar(17) NOT NULL,
	ip varchar(15) NOT NULL,
	hostname varchar(100),
	PRIMARY KEY (addrID)
);

INSERT INTO intune_users(hostname, macaddress, username, email)
VALUES("OMNI-001", "11:22:33:44:55", "Usuario Prueba", "usuario.prueba@klym.com");
