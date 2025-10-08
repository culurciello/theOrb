# AWS EC2 MySQL Setup

## Using MySQL on AWS EC2

The application supports MySQL database when running on AWS EC2 instances using the `--run-on-aws` flag.

### Default Configuration

By default, the application uses these MySQL connection parameters:
- **Host**: localhost
- **User**: orvin
- **Password**: orvin
- **Database**: appdb
- **Port**: 3306

### Running with MySQL

```bash
python app.py --run-on-aws --port 3000
```

### Custom Configuration via Environment Variables

Override the default MySQL settings using environment variables:

```bash
export MYSQL_USER=your_username
export MYSQL_PASSWORD=your_password
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=your_database

python app.py --run-on-aws --port 3000
```

### Setting up MySQL on EC2

1. **Install MySQL Server**:
```bash
sudo yum install mysql-server  # Amazon Linux
# or
sudo apt-get install mysql-server  # Ubuntu
```

2. **Start MySQL**:
```bash
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

3. **Create Database and User**:
```sql
mysql -u root -p

CREATE DATABASE appdb;
CREATE USER 'orvin'@'localhost' IDENTIFIED BY 'orvin';
GRANT ALL PRIVILEGES ON appdb.* TO 'orvin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

4. **Install Python MySQL Connector**:
```bash
pip install mysql-connector-python
```

### Migrating from SQLite to MySQL

The application will automatically create tables in MySQL when you first run it with `--run-on-aws`. Your SQLite data won't be automatically migrated. To migrate:

1. Export data from SQLite
2. Import into MySQL using SQL scripts or a migration tool

### Connection String Format

The application uses SQLAlchemy with this connection string format:
```
mysql+mysqlconnector://user:password@host:port/database
```

### Troubleshooting

**Connection Issues**:
- Verify MySQL is running: `sudo systemctl status mysqld`
- Check firewall allows MySQL port 3306
- Verify credentials are correct

**Permission Issues**:
- Ensure the MySQL user has proper privileges
- Check database exists

**Module Not Found**:
- Install required package: `pip install mysql-connector-python`
