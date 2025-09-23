#!/usr/bin/env python3
"""
Release management script for sicoob-api.

This script helps with version bumping and release preparation.
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


class ReleaseManager:
    """Manages version bumping and release preparation."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.pyproject_path = self.project_root / 'pyproject.toml'
        self.setup_path = self.project_root / 'setup.py'
        self.init_path = self.project_root / 'sicoob' / '__init__.py'

    def get_current_version(self) -> str:
        """Get the current version from pyproject.toml."""
        with open(self.pyproject_path, 'rb') as f:
            data = tomllib.load(f)
        return data['project']['version']

    def parse_version(self, version: str) -> tuple[int, int, int, str]:
        """Parse version string into components."""
        if '-' in version:
            version_part, suffix = version.split('-', 1)
        else:
            version_part, suffix = version, ''

        major, minor, patch = map(int, version_part.split('.'))
        return major, minor, patch, suffix

    def bump_version(self, bump_type: str, prerelease: str | None = None) -> str:
        """Bump version according to semantic versioning."""
        current = self.get_current_version()
        major, minor, patch, suffix = self.parse_version(current)

        if bump_type == 'major':
            major += 1
            minor = 0
            patch = 0
        elif bump_type == 'minor':
            minor += 1
            patch = 0
        elif bump_type == 'patch':
            patch += 1
        else:
            raise ValueError(f'Invalid bump type: {bump_type}')

        new_version = f'{major}.{minor}.{patch}'

        if prerelease:
            new_version += f'-{prerelease}'

        return new_version

    def update_version_files(self, new_version: str) -> None:
        """Update version in all relevant files."""
        current_version = self.get_current_version()

        # Update pyproject.toml
        with open(self.pyproject_path, encoding='utf-8') as f:
            content = f.read()

        content = content.replace(
            f'version = "{current_version}"', f'version = "{new_version}"'
        )

        with open(self.pyproject_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update setup.py
        with open(self.setup_path, encoding='utf-8') as f:
            content = f.read()

        content = content.replace(
            f'version="{current_version}"', f'version="{new_version}"'
        )

        with open(self.setup_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update __init__.py
        with open(self.init_path, encoding='utf-8') as f:
            content = f.read()

        content = content.replace(
            f"__version__ = '{current_version}'",
            f"__version__ = '{new_version}'",
        )

        with open(self.init_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def run_command(
        self, cmd: list[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command."""
        print(f'🔄 Running: {" ".join(cmd)}')
        result = subprocess.run(
            cmd, cwd=self.project_root, capture_output=True, text=True
        )

        if check and result.returncode != 0:
            print(f'❌ Command failed: {" ".join(cmd)}')
            print(f'stdout: {result.stdout}')
            print(f'stderr: {result.stderr}')
            sys.exit(1)

        return result

    def check_git_status(self) -> None:
        """Check if git working directory is clean."""
        result = self.run_command(['git', 'status', '--porcelain'])
        if result.stdout.strip():
            print(
                '❌ Git working directory is not clean. Please commit your changes first.'
            )
            print(result.stdout)
            sys.exit(1)
        print('✅ Git working directory is clean')

    def run_tests(self) -> None:
        """Run tests to ensure everything is working."""
        print('🧪 Running tests...')
        self.run_command(['uv', 'run', 'pytest', 'tests/'])
        print('✅ All tests passed')

    def run_linting(self) -> None:
        """Run linting and formatting checks."""
        print('🔍 Running linting...')
        self.run_command(['ruff', 'check', '.'])
        self.run_command(['ruff', 'format', '--check', '.'])
        print('✅ Linting passed')

    def build_package(self) -> None:
        """Build the package."""
        print('📦 Building package...')
        self.run_command(['python', '-m', 'build'])
        print('✅ Package built successfully')

    def create_tag(self, version: str) -> None:
        """Create a git tag for the version."""
        tag = f'v{version}'
        print(f'🏷️  Creating tag {tag}...')

        # Create annotated tag
        self.run_command(['git', 'tag', '-a', tag, '-m', f'Release {tag}'])
        print(f'✅ Tag {tag} created')

    def prepare_release(
        self, bump_type: str, prerelease: str | None = None, skip_tests: bool = False
    ) -> str:
        """Prepare a new release."""
        print('🚀 Preparing release...')

        # Check git status
        self.check_git_status()

        # Run tests and linting
        if not skip_tests:
            self.run_tests()
            self.run_linting()

        # Bump version
        current_version = self.get_current_version()
        new_version = self.bump_version(bump_type, prerelease)

        print(f'📈 Bumping version: {current_version} -> {new_version}')

        # Update version files
        self.update_version_files(new_version)

        # Build package to verify
        self.build_package()

        print(f'✅ Version updated to {new_version}!')
        print()
        print('📋 Mensagem de commit sugerida (copie e cole):')
        print('─' * 60)
        print(f'🚀 chore: bump version to {new_version}')
        print()
        print('📝 Next steps:')
        print('   1. Review the changes: git diff')
        print('   2. Add files: git add pyproject.toml setup.py sicoob/__init__.py')
        print(
            f'   3. Commit: git commit -m "chore: :bookmark: Bump version to {new_version}"'
        )
        print('   4. Create tag and push: make release-push')
        print('   5. Create GitHub release to trigger PyPI deployment')


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description='Release management for sicoob-api',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s patch              # Bump patch version (0.5.0 -> 0.5.1)
  %(prog)s minor              # Bump minor version (0.5.0 -> 0.6.0)
  %(prog)s major              # Bump major version (0.5.0 -> 1.0.0)
  %(prog)s patch --pre alpha  # Create pre-release (0.5.0 -> 0.5.1-alpha)
  %(prog)s --current          # Show current version
        """,
    )

    parser.add_argument(
        'bump_type',
        nargs='?',
        choices=['major', 'minor', 'patch'],
        help='Type of version bump',
    )

    parser.add_argument(
        '--pre',
        '--prerelease',
        dest='prerelease',
        help='Create a pre-release with the given suffix (alpha, beta, rc1, etc.)',
    )

    parser.add_argument(
        '--current', action='store_true', help='Show current version and exit'
    )

    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running tests and linting (use with caution)',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes',
    )

    args = parser.parse_args()

    manager = ReleaseManager()

    if args.current:
        current = manager.get_current_version()
        print(f'Current version: {current}')
        return

    if not args.bump_type:
        parser.print_help()
        return

    if args.dry_run:
        current = manager.get_current_version()
        new_version = manager.bump_version(args.bump_type, args.prerelease)
        print(f'Would bump version: {current} -> {new_version}')
        return

    try:
        manager.prepare_release(args.bump_type, args.prerelease, args.skip_tests)
        print('🎉 Release preparation completed!')
    except Exception as e:
        print(f'❌ Release preparation failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
