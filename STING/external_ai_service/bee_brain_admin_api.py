#!/usr/bin/env python3
"""
Bee Brain Admin API - Endpoints for managing bee_brain updates

Provides:
- Manual update trigger
- GitHub webhook handler
- Version management
- Status endpoints
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import logging
import subprocess
import hmac
import hashlib
import os

logger = logging.getLogger(__name__)

TAG_NAME_REGEX = r'^[a-zA-Z0-9._-]+$'
MAX_TAG_LENGTH = 64

def is_valid_version_tag(tag: str) -> bool:
    """Validate version tag format - only alphanumeric, dots, hyphens, underscores allowed"""
    import re
    return bool(tag and re.fullmatch(TAG_NAME_REGEX, tag) and len(tag) <= MAX_TAG_LENGTH)

def sanitize_version_tag(tag: str) -> str:
    """
    Sanitize and validate a version tag for safe use in subprocess commands.
    Returns the sanitized tag or raises ValueError if invalid.
    """
    if not tag:
        raise ValueError("Version tag cannot be empty")

    # Strip and normalize
    sanitized = str(tag).strip().lstrip('v')

    if not is_valid_version_tag(sanitized):
        raise ValueError(f"Invalid version tag format: {tag!r}")

    return sanitized

def sanitize_path(path_str: str, must_be_relative: bool = True) -> str:
    """
    Sanitize a path string for safe use.
    Prevents path traversal and other injection attacks.
    """
    if not path_str:
        raise ValueError("Path cannot be empty")

    # Normalize the path
    from pathlib import Path as PathLib
    normalized = str(PathLib(path_str).resolve())

    # Prevent path traversal
    if '..' in path_str:
        raise ValueError("Path traversal not allowed")

    # Check for shell metacharacters
    import re
    if re.search(r'[;&|`$()]', path_str):
        raise ValueError("Invalid characters in path")

    return normalized

# Create blueprint
bee_brain_admin_bp = Blueprint('bee_brain_admin', __name__, url_prefix='/api/admin/bee-brain')

def verify_github_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False

    hash_object = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)

@bee_brain_admin_bp.route('/status', methods=['GET'])
def get_status():
    """Get bee_brain system status"""
    try:
        from .bee_brain_manager import BeeBrainManager

        manager = BeeBrainManager()
        metadata = manager.get_metadata()

        available_versions = manager.list_available_versions()

        return jsonify({
            "success": True,
            "status": {
                "sting_version": manager.sting_version,
                "loaded_brain_version": metadata.get("loaded_version"),
                "available_versions": available_versions,
                "compatibility": metadata.get("compatibility"),
                "metadata": metadata.get("metadata"),
                "created_at": metadata.get("created_at")
            }
        })

    except Exception as e:
        logger.error(f"Error getting bee_brain status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bee_brain_admin_bp.route('/generate', methods=['POST'])
def generate_brain():
    """Generate a new bee_brain version"""
    try:
        data = request.json or {}
        version = data.get('version')  # Optional: specify version
        output_dir = data.get('output_dir')  # Optional: custom output dir

        # Validate and sanitize user inputs
        sanitized_version = None
        sanitized_output = None

        if version:
            try:
                sanitized_version = sanitize_version_tag(version)
            except ValueError as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid version: {e}"
                }), 400

        if output_dir:
            try:
                sanitized_output = sanitize_path(output_dir)
            except ValueError as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid output directory: {e}"
                }), 400

        # Run generator script
        generator_script = Path(__file__).parent / "bee_brain_generator.py"

        if not generator_script.exists():
            return jsonify({
                "success": False,
                "error": "bee_brain_generator.py not found"
            }), 500

        cmd = ["python3", str(generator_script)]

        if sanitized_version:
            cmd.extend(["--version", sanitized_version])

        if sanitized_output:
            cmd.extend(["--output", sanitized_output])

        logger.info(f"Running bee_brain generator: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            logger.info(f"Bee brain generated successfully: {result.stdout}")

            # Reload bee_brain in running service
            from .bee_brain_manager import BeeBrainManager
            manager = BeeBrainManager()
            reload_success = manager.reload()

            return jsonify({
                "success": True,
                "message": "Bee brain generated successfully",
                "output": result.stdout,
                "reloaded": reload_success
            })
        else:
            logger.error(f"Bee brain generation failed: {result.stderr}")
            return jsonify({
                "success": False,
                "error": result.stderr
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Generation timed out (>60s)"
        }), 500
    except Exception as e:
        logger.error(f"Error generating bee_brain: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bee_brain_admin_bp.route('/reload', methods=['POST'])
def reload_brain():
    """Reload bee_brain without regenerating"""
    try:
        from .bee_brain_manager import BeeBrainManager

        manager = BeeBrainManager()
        success = manager.reload()

        if success:
            metadata = manager.get_metadata()

            return jsonify({
                "success": True,
                "message": "Bee brain reloaded successfully",
                "loaded_version": metadata.get("loaded_version"),
                "metadata": metadata
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to reload bee_brain"
            }), 500

    except Exception as e:
        logger.error(f"Error reloading bee_brain: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bee_brain_admin_bp.route('/update', methods=['POST'])
def update_brain():
    """
    Update bee_brain - generates new version and reloads

    Request body:
    {
        "version": "1.0.1",  // optional
        "force": false       // regenerate even if version exists
    }
    """
    try:
        data = request.json or {}
        version = data.get('version')
        force = data.get('force', False)

        # Validate and sanitize version input
        sanitized_version = None
        if version:
            try:
                sanitized_version = sanitize_version_tag(version)
            except ValueError as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid version: {e}"
                }), 400

        from .bee_brain_manager import BeeBrainManager

        manager = BeeBrainManager()

        # Check if version already exists
        if sanitized_version and not force:
            available = manager.list_available_versions()
            if sanitized_version in available:
                return jsonify({
                    "success": False,
                    "error": f"Version {sanitized_version} already exists. Use 'force': true to regenerate."
                }), 400

        # Generate new bee_brain
        generator_script = Path(__file__).parent / "bee_brain_generator.py"
        cmd = ["python3", str(generator_script)]

        if sanitized_version:
            cmd.extend(["--version", sanitized_version])

        logger.info(f"Updating bee_brain: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": f"Generation failed: {result.stderr}"
            }), 500

        # Reload
        reload_success = manager.reload()

        metadata = manager.get_metadata()

        return jsonify({
            "success": True,
            "message": "Bee brain updated successfully",
            "output": result.stdout,
            "loaded_version": metadata.get("loaded_version"),
            "reloaded": reload_success
        })

    except Exception as e:
        logger.error(f"Error updating bee_brain: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@bee_brain_admin_bp.route('/webhook/github', methods=['POST'])
def github_webhook():
    """
    GitHub webhook handler for automatic updates

    Triggers bee_brain regeneration on:
    - New releases
    - Pushes to main branch affecting docs/

    Configure in GitHub:
    - URL: https://your-sting.com/api/admin/bee-brain/webhook/github
    - Content type: application/json
    - Secret: Set GITHUB_WEBHOOK_SECRET env var
    - Events: release, push
    """
    try:
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        secret = os.getenv('GITHUB_WEBHOOK_SECRET')

        if secret:
            if not verify_github_signature(request.data, signature, secret):
                logger.warning("GitHub webhook signature verification failed")
                return jsonify({
                    "success": False,
                    "error": "Invalid signature"
                }), 403
        else:
            logger.warning("GITHUB_WEBHOOK_SECRET not set, skipping signature verification")

        # Parse payload
        payload = request.json
        event_type = request.headers.get('X-GitHub-Event')

        logger.info(f"Received GitHub webhook: {event_type}")

        # Handle release events
        if event_type == 'release':
            action = payload.get('action')
            if action in ['published', 'created']:
                release = payload.get('release', {})
                raw_tag_name = release.get('tag_name', '')

                # SECURITY: Sanitize tag_name to prevent command injection
                # Uses sanitize_version_tag which validates and returns only safe characters
                try:
                    sanitized_tag = sanitize_version_tag(raw_tag_name)
                except ValueError as e:
                    logger.warning(f"Invalid tag_name rejected: {raw_tag_name!r} - {e}")
                    return jsonify({
                        "success": False,
                        "error": "Invalid version tag format"
                    }), 400

                logger.info(f"New release detected: {sanitized_tag}")

                # Generate bee_brain for new version using sanitized input
                generator_script = Path(__file__).parent / "bee_brain_generator.py"
                cmd = ["python3", str(generator_script), "--version", sanitized_tag]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=False)

                if result.returncode == 0:
                    # Reload
                    from .bee_brain_manager import BeeBrainManager
                    manager = BeeBrainManager()
                    manager.reload()

                    return jsonify({
                        "success": True,
                        "message": f"Bee brain generated for release {sanitized_tag}",
                        "version": sanitized_tag
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": f"Generation failed: {result.stderr}"
                    }), 500

        # Handle push events (docs changes)
        elif event_type == 'push':
            ref = payload.get('ref')
            commits = payload.get('commits', [])

            # Only process main/master branch
            if ref in ['refs/heads/main', 'refs/heads/master']:
                # Check if any commit modified docs
                docs_modified = False
                for commit in commits:
                    modified_files = commit.get('modified', []) + commit.get('added', [])
                    if any('docs/' in f or 'README' in f or 'ARCHITECTURE' in f for f in modified_files):
                        docs_modified = True
                        break

                if docs_modified:
                    logger.info("Documentation changes detected, regenerating bee_brain")

                    # Regenerate current version
                    generator_script = Path(__file__).parent / "bee_brain_generator.py"
                    result = subprocess.run(
                        ["python3", str(generator_script)],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode == 0:
                        from .bee_brain_manager import BeeBrainManager
                        manager = BeeBrainManager()
                        manager.reload()

                        return jsonify({
                            "success": True,
                            "message": "Bee brain regenerated due to docs changes"
                        })

        return jsonify({
            "success": True,
            "message": "Webhook received but no action taken",
            "event": event_type
        })

    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
