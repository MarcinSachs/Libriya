<#
Reset and seed the MariaDB `libriya` database for local development.

Usage:
  .\scripts\reset_and_seed.ps1        # prompts for confirmation
  .\scripts\reset_and_seed.ps1 -Yes   # skip confirmation

This script will:
- DROP DATABASE IF EXISTS `libriya`
- CREATE DATABASE `libriya` with utf8mb4
- Run `python manage_db.py init` (migrations)
- Run `python manage_db.py seed`

Make sure:
- You have Docker and docker-compose running
- The MariaDB service is named `mariadb` in docker-compose (default in this repo)
- You have an active Python virtualenv if you want to run `manage_db.py` locally
#>

param(
    [switch]$Yes
)

Write-Host "WARNING: This will DROP and recreate the 'libriya' database in the MariaDB container." -ForegroundColor Yellow
if (-not $Yes) {
    $confirm = Read-Host "Type YES to proceed"
    if ($confirm -ne 'YES') {
        Write-Host "Aborted by user." -ForegroundColor Cyan
        exit 1
    }
}

# Variables (match docker-compose.yml)
$dockerService = 'mariadb'
$containerName = 'libriya_mariadb'
$dbName = 'libriya'

# Drop and recreate database. Prefer using the host Python `pymysql` client
# so we don't rely on the `mysql` CLI being present inside the container.
Write-Host "Dropping and recreating database '$dbName' (connecting to 127.0.0.1:3306)..." -ForegroundColor Green
# Allow overriding root password via host env; otherwise default to docker-compose.yml value.
$rootPass = $env:MARIADB_ROOT_PASSWORD
if (-not $rootPass) { $rootPass = 'root_password' }

# Build a small Python script file to drop/create the database using pymysql
$pyFile = Join-Path $env:TEMP "libriya_reset_db.py"
$pyContent = @"
import pymysql
conn = pymysql.connect(host='127.0.0.1', user='root', password='$rootPass', port=3306)
cur = conn.cursor()
cur.execute("DROP DATABASE IF EXISTS $dbName")
cur.execute("CREATE DATABASE $dbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
conn.commit()
conn.close()
"@
Set-Content -Path $pyFile -Value $pyContent -Encoding UTF8
python $pyFile
$pyExit = $LASTEXITCODE
Remove-Item -Path $pyFile -ErrorAction SilentlyContinue
if ($pyExit -ne 0) {
    Write-Host "Failed to drop/create database using Python/pymysql. Attempting to run inside container as a fallback..." -ForegroundColor Yellow
    # Fallback: attempt to run mysql client inside the container (may not exist)
    $dropCmd = 'mysql -u root -p"$MARIADB_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS ' + $dbName + '; CREATE DATABASE ' + $dbName + ' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
    docker-compose exec $dockerService sh -c $dropCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to drop/create database. Check container logs and credentials." -ForegroundColor Red
        exit 1
    }
}

# Run migrations and seed using local Python (ensure venv active)
Write-Host "Running migrations (manage_db.py init) and seeding (manage_db.py seed)..." -ForegroundColor Green
$env:DATABASE_URL = 'mysql+pymysql://libriya_user:libriya_password@127.0.0.1:3306/libriya?charset=utf8mb4'
python manage_db.py init
if ($LASTEXITCODE -ne 0) {
    Write-Host "manage_db.py init failed." -ForegroundColor Red
    exit 1
}

python manage_db.py seed
if ($LASTEXITCODE -ne 0) {
    Write-Host "manage_db.py seed failed." -ForegroundColor Red
    exit 1
}

Write-Host "Database reset and seed completed successfully." -ForegroundColor Green
Write-Host "You can now start services with: docker-compose up -d" -ForegroundColor Cyan
