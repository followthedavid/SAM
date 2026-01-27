#!/usr/bin/env python3
"""
SAM App Store Builder - Automated App Distribution

Automates the entire iOS/macOS app distribution workflow:
1. Build management (xcodebuild)
2. Code signing and provisioning
3. IPA/DMG creation
4. App Store Connect submission
5. Review status tracking

Usage:
    # Register a project
    builder = AppStoreBuilder()
    builder.register_project("/path/to/MyApp.xcodeproj", "MyApp")

    # Build for App Store
    result = builder.build("MyApp", target="release")

    # Upload to App Store Connect
    builder.upload("MyApp")

    # Check status
    status = builder.get_status("MyApp")

API:
    POST /api/appstore/register   - Register project
    POST /api/appstore/build      - Build app
    POST /api/appstore/upload     - Upload to ASC
    GET  /api/appstore/status     - Get project status
    GET  /api/appstore/projects   - List all projects

Created: 2026-01-21
"""

import os
import sys
import json
import subprocess
import hashlib
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from enum import Enum
import logging
import plistlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_store_builder")


class BuildStatus(Enum):
    """Build status states"""
    NOT_BUILT = "not_built"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"


class SubmissionStatus(Enum):
    """App Store submission states"""
    NOT_SUBMITTED = "not_submitted"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    WAITING_FOR_REVIEW = "waiting_for_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class AppProject:
    """Represents an app project"""
    name: str
    project_path: str  # .xcodeproj or .xcworkspace
    bundle_id: str
    version: str = "1.0.0"
    build_number: str = "1"
    platform: str = "iOS"  # iOS, macOS, visionOS, watchOS, tvOS

    # Build state
    build_status: BuildStatus = BuildStatus.NOT_BUILT
    last_build_time: Optional[str] = None
    last_build_error: Optional[str] = None
    archive_path: Optional[str] = None
    ipa_path: Optional[str] = None

    # Submission state
    submission_status: SubmissionStatus = SubmissionStatus.NOT_SUBMITTED
    last_submission_time: Optional[str] = None
    app_store_id: Optional[str] = None

    # Metadata
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["build_status"] = self.build_status.value
        data["submission_status"] = self.submission_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "AppProject":
        data["build_status"] = BuildStatus(data.get("build_status", "not_built"))
        data["submission_status"] = SubmissionStatus(data.get("submission_status", "not_submitted"))
        return cls(**data)


@dataclass
class BuildResult:
    """Result of a build operation"""
    success: bool
    archive_path: Optional[str] = None
    ipa_path: Optional[str] = None
    error: Optional[str] = None
    build_time_seconds: float = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class AppStoreBuilder:
    """
    Automated App Store distribution system.

    Handles:
    - Project registration and tracking
    - xcodebuild automation
    - Code signing configuration
    - IPA/DMG creation
    - App Store Connect API integration
    """

    # Default paths
    DEFAULT_DB_PATH = Path("/Volumes/David External/SAM_AppStore/projects.json")
    DEFAULT_BUILD_DIR = Path("/Volumes/David External/SAM_AppStore/builds")
    DEFAULT_ARCHIVE_DIR = Path("/Volumes/David External/SAM_AppStore/archives")

    def __init__(
        self,
        db_path: Optional[Path] = None,
        build_dir: Optional[Path] = None,
        archive_dir: Optional[Path] = None,
        asc_api_key: Optional[str] = None,
        asc_issuer_id: Optional[str] = None,
    ):
        """
        Initialize the App Store Builder.

        Args:
            db_path: Path to project database JSON
            build_dir: Directory for build outputs
            archive_dir: Directory for .xcarchive files
            asc_api_key: App Store Connect API key path
            asc_issuer_id: App Store Connect Issuer ID
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.build_dir = build_dir or self.DEFAULT_BUILD_DIR
        self.archive_dir = archive_dir or self.DEFAULT_ARCHIVE_DIR

        # App Store Connect credentials (optional)
        self.asc_api_key = asc_api_key
        self.asc_issuer_id = asc_issuer_id

        # Create directories
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Load project database
        self.projects: Dict[str, AppProject] = {}
        self._load_db()

    def _load_db(self):
        """Load project database from disk"""
        if self.db_path.exists():
            try:
                with open(self.db_path) as f:
                    data = json.load(f)
                    for name, proj_data in data.get("projects", {}).items():
                        self.projects[name] = AppProject.from_dict(proj_data)
                logger.info(f"Loaded {len(self.projects)} projects from database")
            except Exception as e:
                logger.error(f"Failed to load database: {e}")
                self.projects = {}

    def _save_db(self):
        """Save project database to disk"""
        try:
            data = {
                "version": "1.0",
                "updated": datetime.now().isoformat(),
                "projects": {name: proj.to_dict() for name, proj in self.projects.items()}
            }
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.projects)} projects to database")
        except Exception as e:
            logger.error(f"Failed to save database: {e}")

    def register_project(
        self,
        project_path: str,
        name: Optional[str] = None,
        bundle_id: Optional[str] = None,
        platform: str = "iOS",
    ) -> Dict[str, Any]:
        """
        Register an Xcode project for App Store distribution.

        Args:
            project_path: Path to .xcodeproj or .xcworkspace
            name: Project name (derived from path if not provided)
            bundle_id: Bundle identifier (read from project if not provided)
            platform: Target platform (iOS, macOS, etc.)

        Returns:
            Registration result with project info
        """
        project_path = Path(project_path).resolve()

        if not project_path.exists():
            return {"success": False, "error": f"Project not found: {project_path}"}

        # Derive name from project path
        if not name:
            name = project_path.stem.replace(".xcodeproj", "").replace(".xcworkspace", "")

        # Try to read bundle ID from project
        if not bundle_id:
            bundle_id = self._extract_bundle_id(project_path) or f"com.sam.{name.lower()}"

        # Read version info
        version, build = self._extract_version_info(project_path)

        # Create project entry
        project = AppProject(
            name=name,
            project_path=str(project_path),
            bundle_id=bundle_id,
            version=version or "1.0.0",
            build_number=build or "1",
            platform=platform,
        )

        self.projects[name] = project
        self._save_db()

        logger.info(f"Registered project: {name} ({bundle_id})")

        return {
            "success": True,
            "project": project.to_dict(),
            "message": f"Registered {name} for {platform} distribution"
        }

    def _extract_bundle_id(self, project_path: Path) -> Optional[str]:
        """Extract bundle ID from Xcode project"""
        try:
            # Find Info.plist or project.pbxproj
            if project_path.suffix == ".xcodeproj":
                pbxproj = project_path / "project.pbxproj"
                if pbxproj.exists():
                    content = pbxproj.read_text()
                    # Simple regex to find bundle ID
                    import re
                    match = re.search(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^";]+)', content)
                    if match:
                        return match.group(1)
        except Exception as e:
            logger.warning(f"Could not extract bundle ID: {e}")
        return None

    def _extract_version_info(self, project_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Extract version and build number from project"""
        try:
            if project_path.suffix == ".xcodeproj":
                pbxproj = project_path / "project.pbxproj"
                if pbxproj.exists():
                    content = pbxproj.read_text()
                    import re
                    version_match = re.search(r'MARKETING_VERSION\s*=\s*"?([^";]+)', content)
                    build_match = re.search(r'CURRENT_PROJECT_VERSION\s*=\s*"?([^";]+)', content)
                    return (
                        version_match.group(1) if version_match else None,
                        build_match.group(1) if build_match else None
                    )
        except Exception as e:
            logger.warning(f"Could not extract version info: {e}")
        return None, None

    def build(
        self,
        project_name: str,
        scheme: Optional[str] = None,
        configuration: str = "Release",
        destination: Optional[str] = None,
        clean: bool = True,
    ) -> BuildResult:
        """
        Build an app for distribution.

        Args:
            project_name: Name of registered project
            scheme: Xcode scheme (defaults to project name)
            configuration: Build configuration (Release/Debug)
            destination: Build destination (e.g., "generic/platform=iOS")
            clean: Whether to clean before building

        Returns:
            BuildResult with archive and IPA paths
        """
        if project_name not in self.projects:
            return BuildResult(success=False, error=f"Project not found: {project_name}")

        project = self.projects[project_name]
        project.build_status = BuildStatus.BUILDING
        self._save_db()

        start_time = datetime.now()
        scheme = scheme or project.name

        # Determine if workspace or project
        project_path = Path(project.project_path)
        is_workspace = project_path.suffix == ".xcworkspace"

        # Set destination based on platform
        if not destination:
            destinations = {
                "iOS": "generic/platform=iOS",
                "macOS": "generic/platform=macOS",
                "visionOS": "generic/platform=visionOS",
                "watchOS": "generic/platform=watchOS",
                "tvOS": "generic/platform=tvOS",
            }
            destination = destinations.get(project.platform, "generic/platform=iOS")

        # Archive path
        archive_name = f"{project.name}_{project.version}_{project.build_number}.xcarchive"
        archive_path = self.archive_dir / archive_name

        # Build xcodebuild command
        cmd = ["xcodebuild"]

        if is_workspace:
            cmd.extend(["-workspace", str(project_path)])
        else:
            cmd.extend(["-project", str(project_path)])

        cmd.extend([
            "-scheme", scheme,
            "-configuration", configuration,
            "-destination", destination,
            "-archivePath", str(archive_path),
        ])

        if clean:
            cmd.append("clean")
        cmd.append("archive")

        logger.info(f"Building {project.name}: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
            )

            build_time = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0 and archive_path.exists():
                # Extract IPA from archive
                ipa_path = self._export_ipa(archive_path, project)

                project.build_status = BuildStatus.SUCCESS
                project.archive_path = str(archive_path)
                project.ipa_path = str(ipa_path) if ipa_path else None
                project.last_build_time = datetime.now().isoformat()
                project.last_build_error = None
                self._save_db()

                logger.info(f"Build successful: {archive_path}")

                return BuildResult(
                    success=True,
                    archive_path=str(archive_path),
                    ipa_path=str(ipa_path) if ipa_path else None,
                    build_time_seconds=build_time,
                )
            else:
                error = result.stderr or result.stdout or "Unknown build error"
                project.build_status = BuildStatus.FAILED
                project.last_build_error = error[:500]  # Truncate error
                self._save_db()

                logger.error(f"Build failed: {error[:200]}")

                return BuildResult(
                    success=False,
                    error=error,
                    build_time_seconds=build_time,
                )

        except subprocess.TimeoutExpired:
            project.build_status = BuildStatus.FAILED
            project.last_build_error = "Build timed out after 30 minutes"
            self._save_db()
            return BuildResult(success=False, error="Build timed out")
        except Exception as e:
            project.build_status = BuildStatus.FAILED
            project.last_build_error = str(e)
            self._save_db()
            return BuildResult(success=False, error=str(e))

    def _export_ipa(self, archive_path: Path, project: AppProject) -> Optional[Path]:
        """Export IPA from archive using xcodebuild"""
        export_path = self.build_dir / f"{project.name}_{project.version}"
        export_path.mkdir(parents=True, exist_ok=True)

        # Create export options plist
        export_options = {
            "method": "app-store",
            "uploadSymbols": True,
            "uploadBitcode": False,
        }

        options_path = export_path / "ExportOptions.plist"
        with open(options_path, "wb") as f:
            plistlib.dump(export_options, f)

        cmd = [
            "xcodebuild", "-exportArchive",
            "-archivePath", str(archive_path),
            "-exportPath", str(export_path),
            "-exportOptionsPlist", str(options_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                # Find the IPA
                ipas = list(export_path.glob("*.ipa"))
                if ipas:
                    return ipas[0]
            else:
                logger.warning(f"IPA export failed: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"IPA export error: {e}")

        return None

    def upload(
        self,
        project_name: str,
        api_key: Optional[str] = None,
        issuer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload app to App Store Connect.

        Args:
            project_name: Name of built project
            api_key: App Store Connect API key path (or uses default)
            issuer_id: App Store Connect Issuer ID (or uses default)

        Returns:
            Upload result
        """
        if project_name not in self.projects:
            return {"success": False, "error": f"Project not found: {project_name}"}

        project = self.projects[project_name]

        if not project.ipa_path or not Path(project.ipa_path).exists():
            return {"success": False, "error": "No IPA file found. Build first."}

        api_key = api_key or self.asc_api_key
        issuer_id = issuer_id or self.asc_issuer_id

        if not api_key or not issuer_id:
            return {
                "success": False,
                "error": "App Store Connect credentials not configured",
                "hint": "Set asc_api_key and asc_issuer_id in builder config"
            }

        project.submission_status = SubmissionStatus.UPLOADING
        self._save_db()

        # Use xcrun altool or notarytool for upload
        cmd = [
            "xcrun", "altool",
            "--upload-app",
            "--type", "ios",
            "--file", project.ipa_path,
            "--apiKey", api_key,
            "--apiIssuer", issuer_id,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                project.submission_status = SubmissionStatus.PROCESSING
                project.last_submission_time = datetime.now().isoformat()
                self._save_db()

                return {
                    "success": True,
                    "message": f"Uploaded {project.name} to App Store Connect",
                    "status": "processing"
                }
            else:
                project.submission_status = SubmissionStatus.NOT_SUBMITTED
                self._save_db()

                return {
                    "success": False,
                    "error": result.stderr or result.stdout
                }

        except Exception as e:
            project.submission_status = SubmissionStatus.NOT_SUBMITTED
            self._save_db()
            return {"success": False, "error": str(e)}

    def get_status(self, project_name: str) -> Dict[str, Any]:
        """Get status of a project"""
        if project_name not in self.projects:
            return {"success": False, "error": f"Project not found: {project_name}"}

        return {
            "success": True,
            "project": self.projects[project_name].to_dict()
        }

    def list_projects(self) -> Dict[str, Any]:
        """List all registered projects"""
        return {
            "success": True,
            "count": len(self.projects),
            "projects": [p.to_dict() for p in self.projects.values()]
        }

    def increment_build_number(self, project_name: str) -> Dict[str, Any]:
        """Increment build number for a project"""
        if project_name not in self.projects:
            return {"success": False, "error": f"Project not found: {project_name}"}

        project = self.projects[project_name]
        try:
            project.build_number = str(int(project.build_number) + 1)
        except ValueError:
            project.build_number = "1"

        self._save_db()

        return {
            "success": True,
            "new_build_number": project.build_number,
            "message": f"Build number incremented to {project.build_number}"
        }

    def set_version(self, project_name: str, version: str) -> Dict[str, Any]:
        """Set version for a project"""
        if project_name not in self.projects:
            return {"success": False, "error": f"Project not found: {project_name}"}

        project = self.projects[project_name]
        project.version = version
        project.build_number = "1"  # Reset build number on version change
        self._save_db()

        return {
            "success": True,
            "version": version,
            "build_number": "1"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get builder statistics"""
        total = len(self.projects)
        built = sum(1 for p in self.projects.values() if p.build_status == BuildStatus.SUCCESS)
        submitted = sum(1 for p in self.projects.values()
                       if p.submission_status not in (SubmissionStatus.NOT_SUBMITTED,))

        return {
            "total_projects": total,
            "built": built,
            "submitted": submitted,
            "by_platform": self._count_by_platform(),
            "by_status": self._count_by_status(),
        }

    def _count_by_platform(self) -> Dict[str, int]:
        """Count projects by platform"""
        counts = {}
        for p in self.projects.values():
            counts[p.platform] = counts.get(p.platform, 0) + 1
        return counts

    def _count_by_status(self) -> Dict[str, int]:
        """Count projects by build status"""
        counts = {}
        for p in self.projects.values():
            status = p.build_status.value
            counts[status] = counts.get(status, 0) + 1
        return counts


# Singleton instance
_builder_instance = None

def get_builder() -> AppStoreBuilder:
    """Get or create the singleton builder instance"""
    global _builder_instance
    if _builder_instance is None:
        _builder_instance = AppStoreBuilder()
    return _builder_instance


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM App Store Builder")
    subparsers = parser.add_subparsers(dest="command")

    # Register command
    reg_parser = subparsers.add_parser("register", help="Register a project")
    reg_parser.add_argument("project_path", help="Path to .xcodeproj or .xcworkspace")
    reg_parser.add_argument("--name", help="Project name")
    reg_parser.add_argument("--platform", default="iOS", help="Target platform")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build a project")
    build_parser.add_argument("project_name", help="Name of registered project")
    build_parser.add_argument("--scheme", help="Xcode scheme")
    build_parser.add_argument("--no-clean", action="store_true", help="Skip clean")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload to App Store Connect")
    upload_parser.add_argument("project_name", help="Name of built project")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get project status")
    status_parser.add_argument("project_name", help="Project name")

    # List command
    subparsers.add_parser("list", help="List all projects")

    # Stats command
    subparsers.add_parser("stats", help="Get builder statistics")

    args = parser.parse_args()
    builder = get_builder()

    if args.command == "register":
        result = builder.register_project(
            args.project_path,
            name=args.name,
            platform=args.platform
        )
        print(json.dumps(result, indent=2))

    elif args.command == "build":
        result = builder.build(
            args.project_name,
            scheme=args.scheme,
            clean=not args.no_clean
        )
        print(json.dumps(result.to_dict(), indent=2))

    elif args.command == "upload":
        result = builder.upload(args.project_name)
        print(json.dumps(result, indent=2))

    elif args.command == "status":
        result = builder.get_status(args.project_name)
        print(json.dumps(result, indent=2))

    elif args.command == "list":
        result = builder.list_projects()
        print(json.dumps(result, indent=2))

    elif args.command == "stats":
        result = builder.get_stats()
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
