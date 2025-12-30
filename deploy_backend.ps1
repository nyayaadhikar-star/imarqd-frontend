<# 
deploy_backend.ps1
Backend deploy script for IMARQD/Klyvo FastAPI (Docker -> ACR -> Azure Web App for Containers)

Requirements:
- Azure CLI installed (az)
- Docker installed & running
- You are in repo root (contains apps/api/Dockerfile)
#>

$ErrorActionPreference = "Stop"

# -----------------------------
# CONFIG (EDIT THESE)
# -----------------------------
$RESOURCE_GROUP      = "imarqd-backend"          # your RG (you used this in commands)
$LOCATION            = "centralindia"            # only used if creating resources
$ACR_NAME            = "imarqdacr"
$ACR_LOGIN_SERVER    = "$ACR_NAME.azurecr.io"

$APP_SERVICE_PLAN    = "imarqd-plan"
$WEBAPP_NAME         = "imarqd-backend-app"
$SKU                 = "B1"                      # change to B2/S1 later if needed

$IMAGE_REPO          = "imarqd-backend"
$IMAGE_TAG           = "latest"
$FULL_IMAGE          = "$ACR_LOGIN_SERVER/$IMAGE_REPO`:$IMAGE_TAG"

$DOCKERFILE_PATH     = "apps/api/Dockerfile"
$BUILD_CONTEXT       = "."

# ---- Runtime app settings (EDIT VALUES) ----
$DB_HOST             = "imarqd-postgres.postgres.database.azure.com"
$DB_PORT             = 5432
$DB_NAME             = "imarqd_db"
$DB_USER             = "pgadmin"                 # sometimes needs pgadmin@imarqd-postgres (see note below)
$DB_PASSWORD         = "Notebook@123"            # WARNING: special chars will be URL-encoded safely
$DB_SSLMODE          = "require"

$AZURE_STORAGE_CONNECTION_STRING = "PASTE_YOUR_STORAGE_CONNECTION_STRING_HERE"

# NOTE:
# If you get auth errors after deploy, try:
# $DB_USER = "pgadmin@imarqd-postgres"

# -----------------------------
# Helpers
# -----------------------------
function Require-Command($cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Command not found: $cmd. Please install it and retry."
    }
}

function UrlEncode([string]$s) {
    Add-Type -AssemblyName System.Web
    return [System.Web.HttpUtility]::UrlEncode($s)
}

function Az-EnsureLogin {
    try {
        $null = az account show --only-show-errors | Out-Null
    } catch {
        Write-Host "Not logged in. Running az login..." -ForegroundColor Yellow
        az login | Out-Null
    }
}

function Az-ExistsResourceGroup($rg) {
    $exists = az group exists -n $rg --only-show-errors
    return ($exists -eq "true")
}

function Az-EnsureResourceGroup($rg, $loc) {
    if (-not (Az-ExistsResourceGroup $rg)) {
        Write-Host "Creating Resource Group: $rg ($loc)" -ForegroundColor Cyan
        az group create -n $rg -l $loc --only-show-errors | Out-Null
    } else {
        Write-Host "Resource Group exists: $rg" -ForegroundColor Green
    }
}

function Az-EnsureAcr($rg, $acrName, $loc) {
    $acr = az acr show -g $rg -n $acrName --only-show-errors 2>$null
    if (-not $acr) {
        Write-Host "Creating ACR: $acrName" -ForegroundColor Cyan
        az acr create -g $rg -n $acrName --sku Basic -l $loc --only-show-errors | Out-Null
        az acr update -n $acrName --admin-enabled true --only-show-errors | Out-Null
    } else {
        Write-Host "ACR exists: $acrName" -ForegroundColor Green
        # Ensure admin is enabled (simple for now)
        az acr update -n $acrName --admin-enabled true --only-show-errors | Out-Null
    }
}

function Az-EnsureAppServicePlan($rg, $plan, $loc, $sku) {
    $planExists = az appservice plan show -g $rg -n $plan --only-show-errors 2>$null
    if (-not $planExists) {
        Write-Host "Creating App Service Plan (Linux): $plan" -ForegroundColor Cyan
        az appservice plan create -g $rg -n $plan --is-linux --sku $sku -l $loc --only-show-errors | Out-Null
    } else {
        Write-Host "App Service Plan exists: $plan" -ForegroundColor Green
    }
}

function Az-EnsureWebApp($rg, $plan, $webapp, $image) {
    $appExists = az webapp show -g $rg -n $webapp --only-show-errors 2>$null
    if (-not $appExists) {
        Write-Host "Creating Web App (Container): $webapp" -ForegroundColor Cyan
        az webapp create -g $rg -p $plan -n $webapp --deployment-container-image-name $image --only-show-errors | Out-Null
    } else {
        Write-Host "Web App exists: $webapp" -ForegroundColor Green
    }
}

function Az-SetContainerConfig($rg, $webapp, $image, $acrLoginServer, $acrUser, $acrPass) {
    Write-Host "Configuring Web App container image..." -ForegroundColor Cyan
    az webapp config container set `
        -g $rg `
        -n $webapp `
        --docker-custom-image-name $image `
        --docker-registry-server-url "https://$acrLoginServer" `
        --only-show-errors | Out-Null

    Write-Host "Setting registry credentials in app settings..." -ForegroundColor Cyan
    az webapp config appsettings set `
        -g $rg `
        -n $webapp `
        --settings `
        DOCKER_REGISTRY_SERVER_URL="https://$acrLoginServer" `
        DOCKER_REGISTRY_SERVER_USERNAME="$acrUser" `
        DOCKER_REGISTRY_SERVER_PASSWORD="$acrPass" `
        --only-show-errors | Out-Null
}

function Az-SetAppSettings($rg, $webapp, $dbUrl, $storageConn) {
    Write-Host "Setting app settings (PORT, WEBSITES_PORT, DATABASE_URL, Storage)..." -ForegroundColor Cyan
    az webapp config appsettings set `
        -g $rg `
        -n $webapp `
        --settings `
        PORT="8000" `
        WEBSITES_PORT="8000" `
        ENV="production" `
        DATABASE_URL="$dbUrl" `
        AZURE_STORAGE_CONNECTION_STRING="$storageConn" `
        --only-show-errors | Out-Null
}

function Az-RestartAndShowUrl($rg, $webapp) {
    Write-Host "Restarting Web App..." -ForegroundColor Cyan
    az webapp restart -g $rg -n $webapp --only-show-errors | Out-Null

    $host = az webapp show -g $rg -n $webapp --query defaultHostName -o tsv --only-show-errors
    Write-Host ""
    Write-Host "✅ Backend URL:" -ForegroundColor Green
    Write-Host "https://$host/docs" -ForegroundColor Green
    Write-Host ""
}

# -----------------------------
# Main
# -----------------------------
Require-Command az
Require-Command docker

Write-Host "== IMARQD Backend Deploy ==" -ForegroundColor Magenta

Az-EnsureLogin
Az-EnsureResourceGroup $RESOURCE_GROUP $LOCATION
Az-EnsureAcr $RESOURCE_GROUP $ACR_NAME $LOCATION

Write-Host "Logging into ACR..." -ForegroundColor Cyan
az acr login -n $ACR_NAME --only-show-errors | Out-Null

# Build + Push
Write-Host "Building Docker image: $FULL_IMAGE" -ForegroundColor Cyan
docker build -t $FULL_IMAGE -f $DOCKERFILE_PATH $BUILD_CONTEXT

Write-Host "Pushing Docker image to ACR..." -ForegroundColor Cyan
docker push $FULL_IMAGE

# Ensure App Service infra
Az-EnsureAppServicePlan $RESOURCE_GROUP $APP_SERVICE_PLAN $LOCATION $SKU
Az-EnsureWebApp $RESOURCE_GROUP $APP_SERVICE_PLAN $WEBAPP_NAME $FULL_IMAGE

# Get ACR admin creds (simple approach)
$acrUser = az acr credential show -n $ACR_NAME --query username -o tsv --only-show-errors
$acrPass = az acr credential show -n $ACR_NAME --query "passwords[0].value" -o tsv --only-show-errors

Az-SetContainerConfig $RESOURCE_GROUP $WEBAPP_NAME $FULL_IMAGE $ACR_LOGIN_SERVER $acrUser $acrPass

# Build DB URL with safe encoding for password special chars like @
$encodedPass = UrlEncode $DB_PASSWORD
$dbUrl = "postgresql://$DB_USER`:$encodedPass@$DB_HOST`:$DB_PORT/$DB_NAME?sslmode=$DB_SSLMODE"

Az-SetAppSettings $RESOURCE_GROUP $WEBAPP_NAME $dbUrl $AZURE_STORAGE_CONNECTION_STRING

Az-RestartAndShowUrl $RESOURCE_GROUP $WEBAPP_NAME

# Enable container logs + tail
Write-Host "Enabling docker container logs (filesystem)..." -ForegroundColor Cyan
az webapp log config -g $RESOURCE_GROUP -n $WEBAPP_NAME --docker-container-logging filesystem --only-show-errors | Out-Null

Write-Host "Streaming logs (Ctrl+C to stop)..." -ForegroundColor Cyan
az webapp log tail -g $RESOURCE_GROUP -n $WEBAPP_NAME
