# Release Checklist

Follow this checklist to cut a release safely.

1) Prep
- Ensure main is green (CI: lint, typecheck, tests, pack mac pass)
- Update changelog (if maintained) and docs/spec where needed

2) Version bump
- Bump version in app/gui-electron/package.json (semver)
- Optional: tag locally: git tag -a v<version> -m "Release v<version>"; git push --tags

3) Build & verify locally (optional)
- cd app/gui-electron
- npm ci && npm run pack:mac && npm test && npm run typecheck && npm run lint
- Launch packaged app (smoke): npm run open:mac

4) Import workflows (optional refresh)
- ~/ReverseLab/Warp_Open/tools/sync_workflows.sh

5) Push
- Commit version bump and docs
- git push origin main (or open PR and merge)

6) Create GitHub Release
- Option A (automatic): release workflow will tag v<version>, build mac artifact, and publish release
- Option B (manual): create a GitHub release for tag v<version> and upload dist/Warp_Open-darwin-arm64.tgz

7) Post-release checks
- Download artifact from release; launch app; verify:
  - Autosave/restore precedence
  - Preferences, shell spawn, path actions
  - Palette runs items and New Tab action
  - Session JSONL logs appear (~/.warp_open/sessions)

8) Announce
- Summarize changes and link to release notes
