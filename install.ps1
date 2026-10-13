# Fazen Memory installer: links this repo into ~/.claude so every Claude Code chat uses it.
# Idempotent. Anything already there that is not our link is moved to a backup folder, never deleted.
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$claude = Join-Path $env:USERPROFILE '.claude'
$backup = Join-Path $claude ('fazen-memory-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

$links = [ordered]@{}
foreach ($skill in Get-ChildItem (Join-Path $repo 'skills') -Directory) {
    $links[(Join-Path $claude "skills\$($skill.Name)")] = $skill.FullName
}
foreach ($dir in 'hooks', 'tests') {
    $links[(Join-Path $claude "fazen-memory\$dir")] = Join-Path $repo $dir
}

foreach ($link in $links.Keys) {
    $target = $links[$link]
    $item = Get-Item $link -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'Junction' -and $item.Target -eq $target) {
        Write-Host "ok      $link"
        continue
    }
    if ($item) {
        $dest = Join-Path $backup ($link.Substring($claude.Length + 1))
        New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
        Move-Item $link $dest
        Write-Host "backup  $link -> $dest"
    }
    New-Item -ItemType Directory -Force (Split-Path $link) | Out-Null
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    Write-Host "linked  $link -> $target"
}

# Hooks must be registered in settings.json; checked, not edited (a rewrite would reformat the file).
$settings = Get-Content (Join-Path $claude 'settings.json') -Raw
foreach ($hook in 'on_prompt.py', 'on_stop.py') {
    if ($settings -match [regex]::Escape("fazen-memory/hooks/$hook")) {
        Write-Host "ok      hook $hook registered"
    } else {
        Write-Warning "hook $hook NOT registered in settings.json: see README (UserPromptSubmit -> on_prompt.py, Stop -> on_stop.py)"
    }
}
