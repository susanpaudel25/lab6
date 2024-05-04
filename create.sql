
BEGIN TRANSACTION;
DROP TABLE IF EXISTS "users";
CREATE TABLE IF NOT EXISTS "users" (
	"user_id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "username" TEXT,
    "password" TEXT,
    "api_key" TEXT UNIQUE NOT NULL
);
COMMIT;

BEGIN TRANSACTION;
DROP TABLE IF EXISTS "reports";
CREATE TABLE IF NOT EXISTS "reports" (
    "report_id" INTEGER PRIMARY KEY,
    "user_id" INTEGER,
    "entry_date" TEXT,
    "latitude" REAL,
    "longitude" REAL,
    "description" TEXT,
    "path" TEXT,
    "county" TEXT,
    "state" TEXT,
    "username" TEXT,
    "temperature" REAL,
    "humidity" REAL,
    "wind_speed" REAL,
    "rainfall" REAL,
    "category" TEXT,
    "ipaddress" TEXT,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
COMMIT;

