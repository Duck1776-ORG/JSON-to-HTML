# Specify the primary and secondary URLs of the directories you want to list
$primaryUrl = "https://www.example.com/data/"
$secondaryUrl = "https://backup.example.com/data/"

# Specify the target folder where you want to save the files
$targetFolder = "C:\DownloadedFiles"

# Create the target folder if it doesn't exist
if (!(Test-Path -Path $targetFolder)) {
    New-Item -ItemType Directory -Force -Path $targetFolder
}

# Function to get directory listing
function Get-DirectoryListing {
    param([string]$url)
    try {
        $response = Invoke-WebRequest -Uri $url -ErrorAction Stop
        return $response.Links | Where-Object { $_.Href -like "*.json" }
    }
    catch {
        Write-Warning "Failed to get directory listing from $url"
        return $null
    }
}

# Function to retry downloads
function Retry-Download {
    param(
        [string]$fileUrl,
        [string]$filePath,
        [int]$maxRetries = 3,
        [int]$retryDelay = 5,
        [int]$currentFile,
        [int]$totalFiles
    )

    # Check if file already exists
    if (Test-Path $filePath) {
        Write-Host ("File already exists: {0} - {1} of {2}" -f $filePath, $currentFile, $totalFiles)
        return $true
    }

    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            Invoke-WebRequest -Uri $fileUrl -OutFile $filePath -ErrorAction Stop
            Write-Host ("Downloaded: {0} - {1} of {2}" -f $filePath, $currentFile, $totalFiles)
            return $true
        }
        catch {
            Write-Warning "Attempt $i of $maxRetries failed for $fileUrl. Retrying in $retryDelay seconds..."
            Start-Sleep -Seconds $retryDelay
        }
    }
    Write-Error ("Failed to download {0} after {1} attempts - {2} of {3}" -f $fileUrl, $maxRetries, $currentFile, $totalFiles)
    return $false
}

# Get the directory listing from primary URL
$primaryLinks = Get-DirectoryListing -url $primaryUrl

if ($null -eq $primaryLinks) {
    Write-Host "Attempting to use secondary URL..."
    $secondaryLinks = Get-DirectoryListing -url $secondaryUrl
    if ($null -eq $secondaryLinks) {
        Write-Error "Failed to get directory listing from both primary and secondary URLs."
        exit
    }
    $links = $secondaryLinks
    $baseUrl = $secondaryUrl
}
else {
    $links = $primaryLinks
    $baseUrl = $primaryUrl
}

# Get total number of files
$totalFiles = $links.Count

# Download each JSON file with retry and fallback
for ($i = 0; $i -lt $totalFiles; $i++) {
    $link = $links[$i]
    $fileName = $link.Href.Split("/")[-1]
    $filePath = Join-Path -Path $targetFolder -ChildPath $fileName
    $currentFile = $i + 1

    # Try primary URL
    $primaryFileUrl = $primaryUrl + $link.Href
    $success = Retry-Download -fileUrl $primaryFileUrl -filePath $filePath -currentFile $currentFile -totalFiles $totalFiles

    # If primary fails, try secondary URL
    if (!$success) {
        Write-Host "Primary download failed. Attempting secondary URL..."
        $secondaryFileUrl = $secondaryUrl + $link.Href
        $success = Retry-Download -fileUrl $secondaryFileUrl -filePath $filePath -currentFile $currentFile -totalFiles $totalFiles
    }

    # Log if both attempts fail
    if (!$success) {
        "$primaryFileUrl | $secondaryFileUrl" | Out-File -Append -FilePath "$targetFolder\failed_downloads.txt"
        Write-Host ("Failed to download: {0} - {1} of {2}" -f $fileName, $currentFile, $totalFiles)
    }
}
