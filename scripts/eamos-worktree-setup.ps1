# eamos-worktree-setup.ps1 - prepare a git worktree as a parallel-agent lane (Windows).
#
# Why this exists (executable ratchet): Claude Code's worktree.symlinkDirectories
# yields copies or junctions (not real symlinks) without Windows Developer Mode, and
# a fresh lane otherwise boots with an EMPTY node_modules so npm binaries (eslint,
# next, vitest) fail silently. This script links every node_modules the main checkout
# has (native symlink first, junction fallback - junctions need no privilege), copies
# the .worktreeinclude'd gitignored files, verifies and re-sets the repo-local git
# identity, and then verifies the lane toolchain end-to-end. Idempotent - safe to re-run.
#
# PowerShell 5.1 only (no pwsh dependency). This file is pure ASCII. Invoke as:
#   & scripts\eamos-worktree-setup.ps1 .claude\worktrees\<lane>
#   powershell -ExecutionPolicy Bypass -File scripts\eamos-worktree-setup.ps1 .claude\worktrees\<lane>
#
# TEARDOWN: delete a worktree dir with  cmd /c "rmdir /s /q <path>"  then
#   git worktree prune. NEVER use PowerShell  Remove-Item -Recurse  on a worktree:
#   it follows the node_modules junction/symlink and wipes the MAIN node_modules.
#
# Standing rule this pairs with: NEVER run `npm install` inside a worktree (npm v7+
# replaces a linked node_modules with a real folder). Installs run in the MAIN
# checkout only; scripts/guard-worktree-install.mjs enforces this.

param(
  [Parameter(Mandatory = $true)]
  [string]$WorktreePath
)

$ErrorActionPreference = "Stop"
$main = Split-Path -Parent $PSScriptRoot   # repo root (this script lives in scripts/)
$wt = Resolve-Path $WorktreePath | Select-Object -ExpandProperty Path

# Sanity: target must be a git worktree (its .git is a FILE pointing home), not main.
$dotGit = Join-Path $wt ".git"
if (-not (Test-Path $dotGit)) { throw "$wt is not a git checkout (no .git)" }
if ((Get-Item $dotGit -Force) -is [System.IO.DirectoryInfo]) {
  throw "$wt looks like a MAIN checkout (.git is a directory) - refusing"
}

$failures = @()

# --- 1. Link every node_modules the main checkout has (native symlink, junction fallback) ---
$candidates = @("node_modules", "app\web\node_modules", "app\frontend\node_modules")
foreach ($rel in $candidates) {
  $target = Join-Path $main $rel
  if (-not (Test-Path $target)) { continue }   # main lacks this node_modules; skip
  $link = Join-Path $wt $rel
  $parent = Split-Path -Parent $link
  if (-not (Test-Path $parent)) { continue }   # lane checkout lacks this dir
  if (Test-Path $link) {
    $item = Get-Item $link -Force
    if (($item.LinkType -eq "Junction") -or ($item.LinkType -eq "SymbolicLink")) {
      Write-Output "ok (linked): $rel"
      continue
    }
    # Empty real dir = the known silent-failure residue; replace it.
    # Non-empty = someone ran npm install here; refuse (do not destroy their work).
    if (@(Get-ChildItem $link -Force).Count -eq 0) {
      Remove-Item $link -Force
    } else {
      $failures += "$rel is a NON-EMPTY real directory (npm install run in the worktree?) - resolve by hand"
      continue
    }
  }
  $linked = $false
  try {
    New-Item -ItemType SymbolicLink -Path $link -Target $target -ErrorAction Stop | Out-Null
    Write-Output "symlink: $rel"
    $linked = $true
  } catch {
    # Native symlink needs Developer Mode / admin; fall back to a junction (no privilege).
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    Write-Output "junction: $rel"
    $linked = $true
  }
  if (-not $linked) { $failures += "could not link $rel" }
}

# --- 2. Copy the .worktreeinclude'd gitignored files if missing ---
$includes = @("app\backend\.env", "app\web\.env.local")
foreach ($rel in $includes) {
  $src = Join-Path $main $rel
  $dst = Join-Path $wt $rel
  if ((Test-Path $src) -and (-not (Test-Path $dst))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item $src $dst
    Write-Output "copied: $rel"
  }
}
$ctxSrc = Join-Path $main ".context"
$ctxDst = Join-Path $wt ".context"
if ((Test-Path $ctxSrc) -and (-not (Test-Path $ctxDst))) {
  Copy-Item $ctxSrc $ctxDst -Recurse
  Write-Output "copied: .context\ (vault pointer - a lane without it has no product context)"
}

# --- 3. Verify / re-set repo-local git identity (a fresh clone inherits a guessed address) ---
$mainName = (git -C $main config user.name)
$mainEmail = (git -C $main config user.email)
$wtName = (git -C $wt config user.name)
$wtEmail = (git -C $wt config user.email)
if ($mainName -and ($wtName -ne $mainName)) {
  git -C $wt config user.name $mainName
  Write-Output "identity: reset user.name to $mainName"
}
if ($mainEmail -and ($wtEmail -ne $mainEmail)) {
  git -C $wt config user.email $mainEmail
  Write-Output "identity: reset user.email to $mainEmail"
}
$wtEmail = (git -C $wt config user.email)
if (-not $wtEmail) { $failures += "git user.email is empty in the worktree - set it before committing" }
else { Write-Output "git identity: $wtEmail" }

# --- 4. Verify the lane toolchain end-to-end (fail loud, never silently degrade) ---
Push-Location $wt
try {
  $eslintV = (npx --prefix app\web eslint --version 2>$null)
  if (-not $eslintV) {
    # Retry from app\web where eslint is a local dependency.
    Push-Location (Join-Path $wt "app\web")
    try { $eslintV = (npx eslint --version 2>$null) } finally { Pop-Location }
  }
  if (-not $eslintV) { $failures += "npx eslint failed - node_modules link not serving binaries" }
  else { Write-Output "eslint: $eslintV" }

  node scripts\eamos-web-boundary.mjs
  if (-not $?) { $failures += "eamos-web-boundary failed in the worktree" }

  node scripts\eamos-handoff-lint.mjs
  if (-not $?) { $failures += "eamos-handoff-lint failed in the worktree" }
}
finally { Pop-Location }

if ($failures.Count -gt 0) {
  Write-Output ""
  Write-Output "WORKTREE SETUP FAILED:"
  $failures | ForEach-Object { Write-Output "  - $_" }
  exit 1
}
Write-Output ""
Write-Output "WORKTREE READY: $wt"
Write-Output "Reminder: npm installs run in the MAIN checkout only. Teardown: cmd /c rmdir /s /q <path> (never PS Remove-Item -Recurse)."
