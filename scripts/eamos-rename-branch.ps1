<#
.SYNOPSIS
  Promote a long-running development branch to be the new default branch,
  flipping Vercel + reminding for Render. Codifies the Phase-2 sequence ran
  on 2026-05-29 (checkpoint/v2-batches-2026-05-17 -> main).

.DESCRIPTION
  Operations, in order:
    1. Preflight: clean worktree, in eamos repo, gh + vercel + git on PATH.
    2. Fetch origin and confirm both branches exist; show divergence.
    3. Fast-forward push OldBranch -> NewBranch on origin.
    4. Re-link Vercel project so productionBranch = NewBranch
       (vercel git disconnect -> vercel git connect).
    5. Delete origin/OldBranch.
    6. Rename local OldBranch -> NewBranch, set upstream to origin/NewBranch.
    7. Print manual steps: Render dashboard branch flip + token revoke.

  Defaults to -DryRun. Pass -Execute to run for real. Destructive steps
  (5, 6) always prompt for confirmation even with -Execute.

.PARAMETER OldBranch
  Branch being promoted (will be deleted from origin). Default:
  checkpoint/v2-batches-2026-05-17.

.PARAMETER NewBranch
  Target branch name. Default: main.

.PARAMETER VercelProject
  Vercel project slug to relink. Default: eamos-dev.

.PARAMETER Execute
  Actually run the commands. Without this, prints the plan only.

.EXAMPLE
  pwsh scripts/eamos-rename-branch.ps1
  # Dry-run: shows what would happen.

.EXAMPLE
  pwsh scripts/eamos-rename-branch.ps1 -Execute
  # Runs with defaults, prompting before each destructive step.
#>

[CmdletBinding()]
param(
  [string] $OldBranch = 'checkpoint/v2-batches-2026-05-17',
  [string] $NewBranch = 'main',
  [string] $VercelProject = 'eamos-dev',
  [switch] $Execute
)

$ErrorActionPreference = 'Stop'
$dryRun = -not $Execute
$label = if ($dryRun) { '[DRY-RUN]' } else { '[EXECUTE]' }

function Step($n, $msg) { Write-Host ""; Write-Host "$label step $n - $msg" -ForegroundColor Cyan }
function Run($cmd) {
  Write-Host "  > $cmd" -ForegroundColor DarkGray
  if (-not $dryRun) { Invoke-Expression $cmd }
}
function Confirm($prompt) {
  if ($dryRun) { return $true }
  $r = Read-Host "$prompt [y/N]"
  return $r -eq 'y' -or $r -eq 'Y'
}

# ---- 1. Preflight ------------------------------------------------------
Step 1 'preflight checks'
$repoRoot = (git rev-parse --show-toplevel) 2>$null
if (-not $repoRoot) { throw 'not inside a git repo' }
Write-Host "  repo root: $repoRoot"

$dirty = (git status --porcelain) | Where-Object { $_ }
if ($dirty) {
  Write-Host '  worktree is dirty:' -ForegroundColor Yellow
  $dirty | ForEach-Object { Write-Host "    $_" }
  throw 'commit or stash before promoting a branch'
}
Write-Host '  worktree clean: ok'

foreach ($tool in 'git','gh','vercel') {
  $cmd = Get-Command $tool -ErrorAction SilentlyContinue
  if (-not $cmd) { Write-Host "  WARN: $tool not on PATH (some steps will fail)" -ForegroundColor Yellow }
  else { Write-Host "  ${tool}: $($cmd.Source)" }
}

# ---- 2. Fetch + show divergence ----------------------------------------
Step 2 "fetch origin + verify $OldBranch and $NewBranch exist"
Run 'git fetch origin --prune'

$oldRef = git rev-parse --verify "origin/$OldBranch" 2>$null
$newRef = git rev-parse --verify "origin/$NewBranch" 2>$null
if (-not $oldRef) { throw "origin/$OldBranch does not exist" }
if (-not $newRef) { throw "origin/$NewBranch does not exist (cannot ff-push onto it)" }

$ahead = (git rev-list --count "origin/$NewBranch..origin/$OldBranch") | ForEach-Object { $_.Trim() }
$behind = (git rev-list --count "origin/$OldBranch..origin/$NewBranch") | ForEach-Object { $_.Trim() }
Write-Host "  origin/$OldBranch is $ahead ahead, $behind behind origin/$NewBranch"
if ([int]$behind -ne 0) {
  throw "origin/$NewBranch has $behind commits not in origin/$OldBranch - non-ff. Resolve manually."
}

# ---- 3. Fast-forward push OldBranch -> NewBranch -----------------------
Step 3 "fast-forward origin/$NewBranch to origin/$OldBranch"
Run "git push origin ${OldBranch}:${NewBranch}"

# ---- 4. Vercel re-link -------------------------------------------------
Step 4 "Vercel: relink $VercelProject so productionBranch = $NewBranch"
Write-Host "  vercel git disconnect / connect is interactive - follow CLI prompts"
Run "vercel git disconnect --yes"
Run 'vercel git connect'
Write-Host "  verify with: vercel project ls  (or mcp__vercel__get_project)"

# ---- 5. Delete origin/OldBranch ---------------------------------------
Step 5 "delete origin/$OldBranch (destructive)"
if (Confirm "  delete remote branch origin/$OldBranch ?") {
  Run "git push origin --delete $OldBranch"
} else {
  Write-Host '  skipped' -ForegroundColor Yellow
}

# ---- 6. Rename local --------------------------------------------------
Step 6 "rename local $OldBranch -> $NewBranch (if applicable)"
$currentLocal = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentLocal -eq $OldBranch) {
  if (Confirm "  rename local '$OldBranch' to '$NewBranch' and set upstream to origin/$NewBranch ?") {
    Run "git branch -m $OldBranch $NewBranch"
    Run "git branch -u origin/$NewBranch $NewBranch"
  } else {
    Write-Host '  skipped' -ForegroundColor Yellow
  }
} else {
  Write-Host "  local HEAD is '$currentLocal', not '$OldBranch' - nothing to rename"
}

# ---- 7. Manual follow-ups ---------------------------------------------
Step 7 'manual follow-ups (no CLI for these)'
Write-Host @"
  - Render: dashboard -> service -> Settings -> Build & Deploy
      Branch = $NewBranch ; Auto-Deploy off (project policy)
      Verify: mcp__render__get_service or render CLI once installed
  - GitHub: gh api repos/:owner/:repo  -> verify default_branch = $NewBranch
      (was already $NewBranch on 2026-05-29; check if you changed it)
  - Revoke any short-lived API tokens used during the rename
      (Vercel: https://vercel.com/account/tokens)
  - Update agent_handoff/CURRENT.md with the rename result
"@
Write-Host ""
Write-Host "$label done." -ForegroundColor Green
if ($dryRun) { Write-Host 'Re-run with -Execute to actually perform these steps.' -ForegroundColor Yellow }
