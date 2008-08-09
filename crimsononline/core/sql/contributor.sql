INSERT INTO core_contributor 
	(first_name, middle_initial, last_name, created_on, board_number, is_active) 
VALUES 
	('Matt', '', 'Fasman', '2008-05-22', 134, 1);
	
INSERT INTO core_contributor 
	(first_name, middle_initial, last_name, created_on, board_number, is_active) 
VALUES 
	('Dan', '', 'Carroll', '2008-05-22', 135, 1);
	
INSERT INTO core_contributor 
	(first_name, middle_initial, last_name, created_on, board_number, is_active) 
VALUES 
	('Andy', '', 'Lei', '2008-05-22', 136, 1);

INSERT INTO core_contributor 
	(first_name, middle_initial, last_name, created_on, board_number, is_active) 
VALUES 
	('Larry', '', 'Summers', '2008-05-22', NULL, 0);

INSERT INTO "auth_group" VALUES(1,'Arts Board');
INSERT INTO "auth_group" VALUES(2,'Biz Board');
INSERT INTO "auth_group" VALUES(3,'Design Board');
INSERT INTO "auth_group" VALUES(4,'Ed Board');
INSERT INTO "auth_group" VALUES(5,'FM Board');
INSERT INTO "auth_group" VALUES(6,'IT Board');
INSERT INTO "auth_group" VALUES(7,'News Board');
INSERT INTO "auth_group" VALUES(8,'Photo Board');
INSERT INTO "auth_group" VALUES(9,'Sports Board');
INSERT INTO "auth_group" VALUES(10,'Arts Exec');
INSERT INTO "auth_group" VALUES(11,'Biz Exec');
INSERT INTO "auth_group" VALUES(12,'Design Exec');
INSERT INTO "auth_group" VALUES(13,'Ed Exec');
INSERT INTO "auth_group" VALUES(14,'FM Exec');
INSERT INTO "auth_group" VALUES(15,'IT Exec');
INSERT INTO "auth_group" VALUES(16,'News Exec');
INSERT INTO "auth_group" VALUES(17,'Photo Exec');
INSERT INTO "auth_group" VALUES(18,'Sports Exec');

INSERT INTO "auth_user" VALUES(2,'joe','','','','sha1$8d7c5$1471eb99e08bd21152273adf6b3b84c5ed44a3a9',1,1,0,'2008-08-08 22:10:15','2008-08-08 22:10:15');

