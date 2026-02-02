# Database Migration Scripts
# Helper commands for common database operations

# Quick migration workflow
Write-Host "=== Libriya Database Helper ===" -ForegroundColor Cyan

function Show-Menu {
    Write-Host "`n Choose an option:" -ForegroundColor Yellow
    Write-Host "  1. Check database status"
    Write-Host "  2. Create new migration"
    Write-Host "  3. Apply migrations (upgrade)"
    Write-Host "  4. Rollback last migration"
    Write-Host "  5. Show migration history"
    Write-Host "  6. Backup database (MariaDB)"
    Write-Host "  7. Initialize database from scratch"
    Write-Host "  8. Start/Stop MariaDB Docker"
    Write-Host "  0. Exit"
    Write-Host ""
}

function Check-Status {
    Write-Host "`n=== Database Status ===" -ForegroundColor Green
    python manage_db.py status
    Write-Host "`n=== Migration Status ===" -ForegroundColor Green
    flask db current
}

function Create-Migration {
    $description = Read-Host "Migration description"
    if ($description) {
        flask db migrate -m "$description"
        Write-Host "✓ Migration created. Review the file before applying!" -ForegroundColor Green
    }
}

function Apply-Migrations {
    Write-Host "Applying migrations..." -ForegroundColor Yellow
    flask db upgrade
    Write-Host "✓ Done" -ForegroundColor Green
}

function Rollback-Migration {
    $confirm = Read-Host "Are you sure you want to rollback? (yes/no)"
    if ($confirm -eq "yes") {
        flask db downgrade -1
        Write-Host "✓ Rolled back" -ForegroundColor Green
    }
}

function Show-History {
    flask db history
}

function Backup-Database {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $filename = "backup_$timestamp.sql"
    
    Write-Host "Creating backup: $filename" -ForegroundColor Yellow
    docker exec libriya_mariadb mysqldump -u libriya_user -plibriya_password_change_me libriya_db > $filename
    
    if ($?) {
        Write-Host "✓ Backup saved: $filename" -ForegroundColor Green
    } else {
        Write-Host "✗ Backup failed" -ForegroundColor Red
    }
}

function Initialize-Database {
    $confirm = Read-Host "This will initialize the database from scratch. Continue? (yes/no)"
    if ($confirm -eq "yes") {
        python manage_db.py init
    }
}

function Manage-Docker {
    Write-Host "`nDocker Management:" -ForegroundColor Yellow
    Write-Host "  1. Start MariaDB"
    Write-Host "  2. Stop MariaDB"
    Write-Host "  3. Restart MariaDB"
    Write-Host "  4. View logs"
    Write-Host "  5. Check status"
    
    $choice = Read-Host "`nChoice"
    
    switch ($choice) {
        "1" { docker-compose up -d mariadb }
        "2" { docker-compose stop mariadb }
        "3" { docker-compose restart mariadb }
        "4" { docker-compose logs -f mariadb }
        "5" { docker-compose ps }
    }
}

# Main loop
do {
    Show-Menu
    $choice = Read-Host "Your choice"
    
    switch ($choice) {
        "1" { Check-Status }
        "2" { Create-Migration }
        "3" { Apply-Migrations }
        "4" { Rollback-Migration }
        "5" { Show-History }
        "6" { Backup-Database }
        "7" { Initialize-Database }
        "8" { Manage-Docker }
        "0" { 
            Write-Host "Goodbye!" -ForegroundColor Cyan
            exit 
        }
        default { Write-Host "Invalid option" -ForegroundColor Red }
    }
    
    if ($choice -ne "0") {
        Read-Host "`nPress Enter to continue"
    }
} while ($choice -ne "0")
