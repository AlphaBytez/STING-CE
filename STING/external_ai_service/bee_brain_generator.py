#!/usr/bin/env python3
"""
Bee Brain Generator - Creates versioned bee_brain knowledge bases from documentation

Usage:
    python bee_brain_generator.py [--version 1.0.0] [--output bee_brains/]
"""

import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any
import sys

class BeeBrainGenerator:
    """Generates versioned bee_brain JSON files from documentation"""

    def __init__(self, sting_root: Path):
        self.sting_root = sting_root
        self.docs_path = sting_root / "docs"
        self.external_ai_path = sting_root / "external_ai_service"

    def read_version(self) -> str:
        """Read STING version from VERSION file"""
        version_file = self.sting_root / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "1.0.0"

    def calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def load_core_knowledge(self) -> Dict[str, str]:
        """Load core bee brain knowledge (identity, capabilities, etc.)"""
        core_knowledge = {}

        # Core knowledge sections from existing bee_brain files
        core_sections = {
            "identity": "## WHO AM I - BEE'S IDENTITY AND ROLE",
            "platform": "## STING PLATFORM OVERVIEW",
            "system_awareness": "## SYSTEM AWARENESS & INTELLIGENCE",
            "technical_architecture": "## TECHNICAL ARCHITECTURE",
            "security_features": "### Key Security Features"
        }

        # Try to load from existing bee_brain file as template
        brain_files = list(self.external_ai_path.glob("bee_brain_v*.md"))
        if brain_files:
            latest_brain = sorted(brain_files)[-1]
            content = latest_brain.read_text(encoding='utf-8')

            # Extract sections
            for section_name, section_header in core_sections.items():
                start = content.find(section_header)
                if start != -1:
                    # Find next ## heading or end of file
                    next_section = content.find('\n## ', start + 1)
                    if next_section == -1:
                        next_section = len(content)
                    core_knowledge[section_name] = content[start:next_section].strip()

        return core_knowledge

    def load_documentation(self, docs_path: Path) -> Dict[str, Any]:
        """Recursively load all documentation files"""
        documentation = {}

        if not docs_path.exists():
            print(f"Warning: Documentation path not found: {docs_path}")
            return documentation

        # Load markdown files recursively
        for md_file in docs_path.rglob("*.md"):
            try:
                relative_path = md_file.relative_to(docs_path)

                # Create nested structure for subdirectories
                parts = list(relative_path.parts)
                current = documentation

                # Navigate/create nested dict structure
                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Add the file content
                file_name = parts[-1]
                content = md_file.read_text(encoding='utf-8')
                current[file_name] = content

            except Exception as e:
                print(f"Warning: Could not load {md_file}: {e}")

        # Also load root-level docs
        root_docs = ["README.md", "ARCHITECTURE.md", "CONTRIBUTING.md",
                     "SECURITY.md", "CHANGELOG.md"]

        for doc in root_docs:
            doc_path = self.sting_root / doc
            if doc_path.exists():
                try:
                    documentation[doc] = doc_path.read_text(encoding='utf-8')
                except Exception as e:
                    print(f"Warning: Could not load {doc}: {e}")

        return documentation

    def calculate_compatibility_range(self, version: str) -> tuple:
        """Calculate version compatibility range"""
        parts = version.split('.')
        major = parts[0]

        min_version = f"{major}.0.0"
        max_version = f"{major}.999.999"

        return min_version, max_version

    def generate_bee_brain(self, version: str = None, output_dir: Path = None) -> Path:
        """Generate a versioned bee_brain JSON file"""

        if version is None:
            version = self.read_version()

        if output_dir is None:
            output_dir = self.external_ai_path / "bee_brains"

        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🐝 Generating Bee Brain v{version}")
        print(f"   STING Root: {self.sting_root}")
        print(f"   Docs Path: {self.docs_path}")
        print(f"   Output: {output_dir}")

        # Load core knowledge
        print("   Loading core knowledge...")
        core_knowledge = self.load_core_knowledge()

        # Load documentation
        print("   Loading documentation...")
        documentation = self.load_documentation(self.docs_path)

        # Calculate metadata
        doc_json = json.dumps(documentation)
        total_size_kb = len(doc_json.encode('utf-8')) / 1024
        checksum = self.calculate_checksum(doc_json)

        def count_docs(d):
            count = 0
            for v in d.values():
                if isinstance(v, dict):
                    count += count_docs(v)
                else:
                    count += 1
            return count

        total_docs = count_docs(documentation)

        min_ver, max_ver = self.calculate_compatibility_range(version)

        # Build bee_brain structure
        bee_brain = {
            "version": version,
            "sting_version_compatibility": {
                "min": min_ver,
                "max": max_ver,
                "recommended": version
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "bee_brain_generator",
            "metadata": {
                "total_docs": total_docs,
                "total_size_kb": round(total_size_kb, 2),
                "checksum": checksum,
                "format_version": "1.0"
            },
            "core_knowledge": core_knowledge,
            "documentation": documentation,
            "version_notes": f"Bee Brain for STING v{version}"
        }

        # Write to file
        output_file = output_dir / f"bee_brain_v{version}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bee_brain, f, indent=2, ensure_ascii=False)

        print(f"✅ Generated: {output_file}")
        print(f"   Docs: {total_docs} files")
        print(f"   Size: {total_size_kb:.2f} KB")
        print(f"   Compatibility: {min_ver} - {max_ver}")

        return output_file

def main():
    parser = argparse.ArgumentParser(description='Generate versioned Bee Brain knowledge base')
    parser.add_argument('--version', help='Bee Brain version (default: read from VERSION file)')
    parser.add_argument('--output', help='Output directory (default: external_ai_service/bee_brains/)')
    parser.add_argument('--sting-root', help='STING root directory (default: parent of script dir)')

    args = parser.parse_args()

    # Determine STING root
    if args.sting_root:
        sting_root = Path(args.sting_root)
    else:
        # Default: parent directory of this script's directory
        sting_root = Path(__file__).parent.parent

    if not sting_root.exists():
        print(f"Error: STING root not found: {sting_root}")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = None  # Will default to bee_brains/ in generator

    # Generate bee brain
    generator = BeeBrainGenerator(sting_root)
    output_file = generator.generate_bee_brain(version=args.version, output_dir=output_dir)

    print(f"\n🎉 Bee Brain generation complete!")
    print(f"   File: {output_file}")

if __name__ == "__main__":
    main()
