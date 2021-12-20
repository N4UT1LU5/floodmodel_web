# Floodmodelling

## CLI flood model script

input -> DGM raster and river shapefile  
output <- floodzone shape

## Setup

### Python

Create virtual environment named gis\
`python3 -m venv gis`

install all packages listed in pip.txt file\
`pip install -r pip.txt`

save all installed packages to pip.txt file\
`pip freeze > pip.txt`

### PostgreSQL

install PostgreSQL\
`sudo apt-get -y install postgresql`

add password to postgres default user\
`sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"`\
**⚠Password now visible in postgres command history⚠** \
Delete history if necessary

open postgres config file\
`sudo nano /etc/postgresql/12/main/postgresql.conf`\
uncomment or set: `listen_addresses = 'localhost'`

start/stop/restart\
`postgresql database\ sudo service postgresql start/stop/restart`

You now can connect to the database in WSL via pgAdmin on the host machine!

### PostGIS

install postgis\
`sudo apt install postgis`\
add postgis to your database via pgAdmin or as a query: `CREATE EXTENSION postgis;`

## Todo
