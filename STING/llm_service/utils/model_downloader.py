#!/usr/bin/env python3
"""
Model downloader utility for STING LLM services
Handles downloading, validating, and preparing models from Hugging Face
"""

import os
import sys
import argparse
import logging
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import requests
import warnings
from tqdm import tqdm
from huggingface_hub import snapshot_download, HfApi, login
from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model-downloader")

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
# Model configuration
MODEL_CONFIGS = {
    "llama3": {
        "repo_id": "meta-llama/Llama-3.1-8B",
        "revision": "main",
        "target_dir": "llama-3-8b",
        "required_files": ["config.json", "tokenizer.json", "tokenizer_config.json"],
        "quantized": True,
        "description": "Meta's Llama 3 (8B) - General purpose model with strong capabilities",
    },
    "phi3": {
        "repo_id": "microsoft/Phi-3-medium-128k-instruct",
        "revision": "main",
        "target_dir": "phi-3-medium-128k-instruct",
        "required_files": ["config.json", "tokenizer.json", "tokenizer_config.json"],
        "quantized": True,
        "description": "Microsoft's Phi-3 Medium - Specialized for information and knowledge tasks",
    },
    "zephyr": {
        "repo_id": "HuggingFaceH4/zephyr-7b-beta",
        "revision": "main",
        "target_dir": "zephyr-7b",
        "required_files": ["config.json", "tokenizer.json", "tokenizer_config.json"],
        "quantized": True,
        "description": "Zephyr 7B - Fine-tuned for technical and code tasks",
    }
}

## Default models directory (can be overridden by STING_MODELS_DIR env)
DEFAULT_MODELS_DIR = os.environ.get("STING_MODELS_DIR", "/opt/models")
# Use standard temp directory for better cross-system compatibility
TEMP_DOWNLOAD_DIR = os.path.join("/tmp", "sting_model_downloads")
CHECKSUM_FILE = "checksums.json"
HF_TOKEN_ENV = "HF_TOKEN"

def calculate_checksum(file_path: str) -> str:
    """Calculate SHA-256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256.update(byte_block)
    return sha256.hexdigest()

def save_checksums(model_dir: str, checksums: Dict[str, str]) -> None:
    """Save checksums of model files to a JSON file"""
    checksum_path = os.path.join(model_dir, CHECKSUM_FILE)
    with open(checksum_path, "w") as f:
        json.dump(checksums, f, indent=2)
    logger.info(f"Saved checksums to {checksum_path}")

def load_checksums(model_dir: str) -> Dict[str, str]:
    """Load previously saved checksums from a JSON file"""
    checksum_path = os.path.join(model_dir, CHECKSUM_FILE)
    if not os.path.exists(checksum_path):
        return {}
    
    with open(checksum_path, "r") as f:
        return json.load(f)

def validate_model(model_dir: str, required_files: List[str]) -> Tuple[bool, List[str]]:
    """Validate that all required model files are present and have correct checksums"""
    missing_files = []
    
    # First check if required files exist
    for file in required_files:
        file_path = os.path.join(model_dir, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        return False, missing_files
    
    # If we have checksums, validate file integrity
    stored_checksums = load_checksums(model_dir)
    if stored_checksums:
        for file, stored_checksum in stored_checksums.items():
            file_path = os.path.join(model_dir, file)
            if os.path.exists(file_path):
                current_checksum = calculate_checksum(file_path)
                if current_checksum != stored_checksum:
                    logger.warning(f"Checksum mismatch for {file}")
                    missing_files.append(file)
    
    return len(missing_files) == 0, missing_files

def download_model(model_name: str, models_dir: str, force: bool = False, token: Optional[str] = None) -> bool:
    """Download a model from Hugging Face Hub"""
    if model_name not in MODEL_CONFIGS:
        logger.error(f"Unknown model: {model_name}")
        return False
    
    if token is None:
        token = os.environ.get("HF_TOKEN")
        if token:
            logger.info(f"Using token from environment variable")
        else:
            logger.warning("No Hugging Face token provided, attempting anonymous download")
    
    config = MODEL_CONFIGS[model_name]
    repo_id = config["repo_id"]
    revision = config["revision"]
    target_dir = os.path.join(models_dir, config["target_dir"])
    
    # Create models directory if it doesn't exist
    os.makedirs(models_dir, exist_ok=True)
    
    # Check if model already exists and is valid
    if os.path.exists(target_dir) and not force:
        logger.info(f"Model directory already exists at {target_dir}")
        valid, missing = validate_model(target_dir, config["required_files"])
        if valid:
            logger.info(f"Model {model_name} is already downloaded and valid")
            return True
        else:
            logger.warning(f"Model {model_name} is incomplete. Missing files: {missing}")
            # Continue with download to fix missing files
    
    # Ensure target model directory exists
    os.makedirs(target_dir, exist_ok=True)
    
    # Create and use a model-specific temporary directory to avoid conflicts
    temp_download_dir = os.path.join(TEMP_DOWNLOAD_DIR, model_name)
    
    # Ensure temp directory exists and is empty
    if os.path.exists(temp_download_dir):
        logger.info(f"Cleaning existing temporary directory: {temp_download_dir}")
        try:
            shutil.rmtree(temp_download_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up existing temp dir, will try to continue: {e}")
    
    # Create a fresh temp directory
    os.makedirs(temp_download_dir, exist_ok=True)
    logger.info(f"Using temporary download directory: {temp_download_dir}")
    
    # Create the parent models directory if it doesn't exist
    if not os.path.exists(models_dir):
        logger.info(f"Creating models directory: {models_dir}")
        os.makedirs(models_dir, exist_ok=True)
    
    try:
        logger.info(f"Downloading {model_name} from {repo_id} into {target_dir}")
        # Authenticate with Hugging Face if token provided
        if token:
            try:
                login(token=token)
                logger.info("Authenticated with Hugging Face")
            except Exception as e:
                logger.warning(f"Authentication warning (continuing anyway): {e}")
                # Continue with the token even if login command failed
        
        # Download to temp directory first
        logger.info(f"Downloading to temporary directory first: {temp_download_dir}")
        try:
            logger.debug(f"Attempting to download {repo_id} (revision: {revision})")
            logger.debug(f"Using token: {'Yes' if token else 'No'}")
            
            # Check if repo exists before attempting download
            try:
                api = HfApi(token=token)
                repo_info = api.repo_info(repo_id=repo_id, revision=revision)
                logger.debug(f"Repository exists: {repo_id} (size: {repo_info.size_on_disk if hasattr(repo_info, 'size_on_disk') else 'unknown'})")
            except Exception as e:
                logger.warning(f"Could not validate repository before download: {e}")
            
            # Attempt download with detailed error capture
            # Check huggingface_hub version to determine which parameters to use
            import pkg_resources
            hf_version = pkg_resources.get_distribution("huggingface_hub").version
            logger.debug(f"huggingface_hub version: {hf_version}")
            
            # Base parameters that work with all versions
            download_params = {
                "repo_id": repo_id,
                "revision": revision,
                "local_dir": temp_download_dir,
                "token": token,
                "resume_download": True,
                "local_files_only": False,
                "tqdm_class": tqdm
            }
            
            # Add retry parameter only if supported by the installed version
            try:
                # First try using packaging for proper version comparison
                try:
                    from packaging import version
                    if version.parse(hf_version) >= version.parse("0.10.0"):
                        download_params["retry"] = 3
                        logger.debug("Using retry parameter (supported in this huggingface_hub version)")
                except ImportError:
                    # Fallback to simple string comparison if packaging is not available
                    major, minor = hf_version.split(".")[:2]
                    if int(major) > 0 or (int(major) == 0 and int(minor) >= 10):
                        download_params["retry"] = 3
                        logger.debug("Using retry parameter (based on simple version comparison)")
                    else:
                        logger.debug("Not using retry parameter (version below 0.10.0)")
            except Exception as e:
                # If all version detection fails, don't use retry to be safe
                logger.debug(f"Not using retry parameter due to error: {e}")
            
            # Execute the download with appropriate parameters
            snapshot_download(**download_params)
            
            # Verify download succeeded
            if not os.path.exists(temp_download_dir) or not os.listdir(temp_download_dir):
                raise RuntimeError(f"Download completed but no files were found in {temp_download_dir}")
                
        except Exception as e:
            logger.error(f"Download failed: {type(e).__name__}: {str(e)}")
            if "401 Client Error" in str(e):
                logger.error("Authentication error - check your HF_TOKEN is valid and has access to this model")
            elif "404 Client Error" in str(e):
                logger.error(f"Model not found - check that {repo_id} exists and is public or your token has access")
            elif "gated repo" in str(e).lower():
                logger.error(f"This model requires accepting terms of use on the HuggingFace website: https://huggingface.co/{repo_id}")
            raise
        
        # Copy files from temp directory to target directory
        logger.info(f"Moving files from {temp_download_dir} to {target_dir}")
        try:
            # First verify that files were successfully downloaded to temp directory
            if not os.listdir(temp_download_dir):
                raise RuntimeError(f"No files downloaded to temporary directory: {temp_download_dir}")
                
            # Copy the files one by one
            file_count = 0
            for item in os.listdir(temp_download_dir):
                src_path = os.path.join(temp_download_dir, item)
                dst_path = os.path.join(target_dir, item)
                
                if os.path.isdir(src_path):
                    if os.path.exists(dst_path):
                        logger.info(f"Removing existing directory: {dst_path}")
                        shutil.rmtree(dst_path)
                    logger.info(f"Copying directory: {item}")
                    shutil.copytree(src_path, dst_path)
                else:
                    logger.info(f"Copying file: {item}")
                    shutil.copy2(src_path, dst_path)
                file_count += 1
            
            logger.info(f"Successfully copied {file_count} items to {target_dir}")
            
        except Exception as e:
            logger.error(f"Error copying files from temp directory: {e}")
            raise RuntimeError(f"Failed to copy model files: {e}") from e
        
        # Calculate checksums for downloaded files
        checksums = {}
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, target_dir)
                checksums[rel_path] = calculate_checksum(file_path)
        
        # Save checksums and validate downloaded model
        save_checksums(target_dir, checksums)
        valid, missing = validate_model(target_dir, config["required_files"])
        if valid:
            logger.info(f"Model {model_name} downloaded successfully")
            return True
        else:
            logger.error(f"Downloaded model {model_name} is missing required files: {missing}")
            return False
    
    except RepositoryNotFoundError:
        logger.error(f"Repository {repo_id} not found. Check if the model name is correct.")
        return False
    except RevisionNotFoundError:
        logger.error(f"Revision {revision} not found for repository {repo_id}")
        return False
    except Exception as e:
        logger.error(f"Error downloading model {model_name}: {str(e)}")
        return False
    finally:
        # Clean up temporary download directory
        if os.path.exists(temp_download_dir):
            logger.info(f"Cleaning up temporary directory: {temp_download_dir}")
            try:
                shutil.rmtree(temp_download_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")
        
        # Make sure permissions are set correctly on the model directory
        if os.path.exists(target_dir):
            for root, dirs, files in os.walk(target_dir):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o755)
                for f in files:
                    os.chmod(os.path.join(root, f), 0o644)

def list_models() -> None:
    """List all available models with their descriptions"""
    print("\nAvailable models:\n")
    for name, config in MODEL_CONFIGS.items():
        print(f"  {name}:")
        print(f"    Description: {config['description']}")
        print(f"    Repository: {config['repo_id']}")
        print(f"    Target directory: {config['target_dir']}")
        print(f"    Quantized: {'Yes' if config['quantized'] else 'No'}")
        print()

def cleanup_temp_directories():
    """Clean up any temporary download directories from previous runs"""
    if os.path.exists(TEMP_DOWNLOAD_DIR):
        logger.info(f"Cleaning up temporary download directory: {TEMP_DOWNLOAD_DIR}")
        try:
            # Remove all contents but keep the directory
            for item in os.listdir(TEMP_DOWNLOAD_DIR):
                item_path = os.path.join(TEMP_DOWNLOAD_DIR, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directories: {e}")

def main():
    # Clean up any temporary directories from previous runs
    cleanup_temp_directories()
    
    parser = argparse.ArgumentParser(description="Download and manage LLM models for STING")
    parser.add_argument("--list", action="store_true", help="List all available models")
    parser.add_argument("--download", nargs="+", help="Download specified models")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--force", action="store_true", help="Force re-download even if model exists")
    parser.add_argument("--validate", nargs="+", help="Validate specified models")
    parser.add_argument("--dir", default=DEFAULT_MODELS_DIR, help="Models directory (default: /app/models)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Get Hugging Face token from environment
    hf_token = os.environ.get(HF_TOKEN_ENV)
    if hf_token:
        logger.info("HF_TOKEN environment variable is set")
    else:
        logger.warning("HF_TOKEN environment variable is not set - downloads may fail for gated models")
    
    if args.list:
        list_models()
        return 0
    
    if args.validate:
        success = True
        for model_name in args.validate:
            if model_name not in MODEL_CONFIGS:
                logger.error(f"Unknown model: {model_name}")
                success = False
                continue
                
            config = MODEL_CONFIGS[model_name]
            target_dir = os.path.join(args.dir, config["target_dir"])
            
            if not os.path.exists(target_dir):
                logger.error(f"Model directory does not exist: {target_dir}")
                success = False
                continue
                
            valid, missing = validate_model(target_dir, config["required_files"])
            if valid:
                logger.info(f"Model {model_name} is valid")
            else:
                logger.error(f"Model {model_name} is missing required files: {missing}")
                success = False
        
        return 0 if success else 1
    
    if args.download or args.all:
        models_to_download = list(MODEL_CONFIGS.keys()) if args.all else args.download
        success = True
        
        for model_name in models_to_download:
            if download_model(model_name, args.dir, args.force, hf_token):
                logger.info(f"Successfully downloaded {model_name}")
            else:
                logger.error(f"Failed to download {model_name}")
                success = False
        
        return 0 if success else 1
    
    # If no action specified, show help
    parser.print_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())
