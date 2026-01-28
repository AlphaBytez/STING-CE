"""
Honey Jar Service - Extracted from working setup scripts
Provides reusable honey jar operations for knowledge service integration
"""

import os
import logging
import requests
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class HoneyJarService:
    """Service for honey jar operations with knowledge service"""

    def __init__(self, knowledge_service_url: str = None, api_key: str = None):
        self.knowledge_url = knowledge_service_url or os.environ.get('KNOWLEDGE_SERVICE_URL', 'http://knowledge:8090')
        self.api_key = api_key or os.environ.get('STING_API_KEY', 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0')
        self.session_token = None

    def get_admin_session(self) -> Optional[str]:
        """Get admin session token for knowledge service authentication"""
        # Extracted from your working setup_default_honey_jars.py
        admin_password_file = os.path.expanduser("~/.sting-ce/admin_password.txt")

        if os.path.exists(admin_password_file):
            with open(admin_password_file, 'r') as f:
                admin_password = f.read().strip()
        else:
            admin_password = "Password1!"  # Default fallback

        try:
            login_response = requests.post(
                f"{self.knowledge_url}/admin/login",
                json={
                    "email": "admin@sting.local",
                    "password": admin_password
                },
                timeout=10
            )

            if login_response.status_code == 200:
                response_data = login_response.json()
                session_token = response_data.get('session_token')
                if session_token:
                    logger.info("✅ Admin authentication successful for honey jar operations")
                    self.session_token = session_token
                    return session_token

            logger.error("❌ Admin authentication failed for honey jar service")
            return None

        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return None

    def create_honey_jar(self, name: str, description: str, jar_type: str = "public", tags: List[str] = None) -> Optional[str]:
        """Create a new honey jar via knowledge service API"""
        # Use API key authentication (which we confirmed works)
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        data = {
            "name": name,
            "description": description,
            "type": jar_type,
            "tags": tags or []
        }

        try:
            response = requests.post(f"{self.knowledge_url}/honey-jars", json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                jar = response.json()
                jar_id = jar.get('id')
                logger.info(f"✅ Created honey jar: {name} (ID: {jar_id})")
                return jar_id
            else:
                logger.warning(f"❌ Failed to create honey jar {name}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Error creating honey jar {name}: {str(e)}")
            return None

    def upload_document(self, jar_id: str, file_path: str, tags: List[str] = None) -> bool:
        """Upload a document to a honey jar"""
        if not os.path.exists(file_path):
            logger.warning(f"⚠️ File not found: {file_path}")
            return False

        # Use API key authentication
        headers = {"X-API-Key": self.api_key}
        filename = os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f, 'text/plain')}
                data = {'tags': tags or ['demo', 'healthcare']}

                response = requests.post(
                    f"{self.knowledge_url}/honey-jars/{jar_id}/documents/upload",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )

                if response.status_code == 200:
                    logger.info(f"✅ Uploaded document: {filename} to jar {jar_id}")
                    return True
                else:
                    logger.warning(f"❌ Failed to upload {filename}: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {str(e)}")
            return False

    def upload_text_content(self, jar_id: str, filename: str, content: str, tags: List[str] = None) -> bool:
        """Upload text content as a document to a honey jar"""
        # Use API key authentication
        headers = {"X-API-Key": self.api_key, "Content-Type": "multipart/form-data"}

        try:
            # Ensure jar_id is properly formatted as UUID string
            import uuid
            jar_uuid = str(uuid.UUID(jar_id))  # Validates and normalizes UUID format

            files = {'file': (filename, content.encode('utf-8'), 'text/plain')}
            # Convert tags list to proper format - avoid nested arrays
            if tags:
                tag_data = [('tags', tag) for tag in tags]
            else:
                tag_data = [('tags', 'demo'), ('tags', 'healthcare')]

            response = requests.post(
                f"{self.knowledge_url}/honey-jars/{jar_uuid}/documents/upload",
                files=files,
                data=tag_data,
                headers={"X-API-Key": self.api_key},  # Remove Content-Type for multipart
                timeout=60
            )

            if response.status_code == 200:
                logger.info(f"✅ Uploaded text content: {filename} to jar {jar_id}")
                return True
            else:
                logger.warning(f"❌ Failed to upload {filename}: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {str(e)}")
            return False

    def get_documents(self, honey_jar_id: str, db = None) -> List[Dict[str, Any]]:
        """Get all documents in a honey jar with direct database access"""
        try:
            # Import here to avoid circular imports
            from app.utils.database import get_db_session
            from sqlalchemy import text
            import uuid

            # Validate and convert honey_jar_id if needed
            if isinstance(honey_jar_id, str):
                try:
                    # Try to parse as UUID
                    uuid.UUID(honey_jar_id)
                    jar_uuid = honey_jar_id
                except ValueError:
                    logger.error(f"Invalid UUID format: {honey_jar_id}")
                    return []

            # Use provided db session or get new one
            if db is None:
                with get_db_session() as session:
                    return self._query_documents(session, jar_uuid)
            else:
                return self._query_documents(db, jar_uuid)

        except Exception as e:
            logger.error(f"Error retrieving documents for honey jar {honey_jar_id}: {str(e)}")
            logger.exception("Full traceback:")
            return []

    def _query_documents(self, db, jar_uuid: str) -> List[Dict[str, Any]]:
        """Query documents from database with proper error handling"""
        from sqlalchemy import text
        import os

        # Query documents with proper joins and error handling
        query = text("""
            SELECT
                d.id,
                d.filename,
                d.content_type,
                d.size_bytes,
                d.upload_date,
                d.status,
                d.doc_metadata,
                d.tags,
                d.file_path,
                d.processing_time,
                d.embedding_count
            FROM documents d
            WHERE d.honey_jar_id = :honey_jar_id
            AND d.status != 'deleted'
            ORDER BY d.upload_date DESC
        """)

        result = db.execute(query, {"honey_jar_id": jar_uuid})
        documents = []

        for row in result:
            # Check if file exists and add flag
            file_exists = False
            if row.file_path:
                file_exists = os.path.exists(row.file_path)
                if not file_exists:
                    logger.debug(f"⚠️ File not found on disk: {row.file_path}")

            doc = {
                "id": str(row.id),
                "filename": row.filename,
                "content_type": row.content_type,
                "size_bytes": row.size_bytes,
                "upload_date": row.upload_date.isoformat() if row.upload_date else None,
                "status": row.status,
                "metadata": row.doc_metadata or {},
                "tags": row.tags or [],
                "file_path": row.file_path,
                "file_exists": file_exists,  # Add flag for frontend
                "processing_time": row.processing_time,
                "embedding_count": row.embedding_count or 0
            }
            documents.append(doc)

        logger.info(f"✅ Retrieved {len(documents)} documents for honey jar {jar_uuid} via database")
        return documents

    def get_honey_jar_stats(self, jar_id: str) -> Dict[str, Any]:
        """Get honey jar statistics including document count"""
        headers = {"X-API-Key": self.api_key}

        try:
            response = requests.get(
                f"{self.knowledge_url}/honey-jars/{jar_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                jar_data = response.json()
                logger.info(f"✅ Retrieved stats for honey jar {jar_id}")
                return jar_data
            else:
                logger.warning(f"❌ Failed to get honey jar stats {jar_id}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"❌ Error getting honey jar stats {jar_id}: {str(e)}")
            return {}

    def create_demo_honey_jars(self, scenario: str) -> List[Dict[str, str]]:
        """Create scenario-specific demo honey jars"""
        if scenario == 'healthcare':
            jar_configs = [
                {"name": "Patient Records Demo", "description": "Demo patient intake forms and medical records with realistic PII", "tags": ["healthcare", "phi", "demo"]},
                {"name": "Lab Results Demo", "description": "Demo laboratory reports and test results with medical data", "tags": ["healthcare", "lab-data", "demo"]},
                {"name": "Prescription Demo", "description": "Demo prescription forms with DEA numbers and medication data", "tags": ["healthcare", "prescriptions", "demo"]},
                {"name": "HIPAA Compliance Demo", "description": "Demo documents for HIPAA compliance testing and validation", "tags": ["compliance", "hipaa", "demo"]}
            ]
        elif scenario == 'comprehensive':
            jar_configs = [
                {"name": "Medical Records Demo", "description": "Comprehensive medical record samples", "tags": ["healthcare", "demo"]},
                {"name": "Legal Documents Demo", "description": "Legal contract and case file samples", "tags": ["legal", "demo"]},
                {"name": "Financial Data Demo", "description": "Financial document samples with PCI data", "tags": ["financial", "demo"]},
                {"name": "HR Files Demo", "description": "Human resources document samples", "tags": ["hr", "demo"]},
                {"name": "Compliance Reports Demo", "description": "Regulatory compliance document samples", "tags": ["compliance", "demo"]}
            ]
        else:  # basic
            jar_configs = [
                {"name": "Healthcare Demos", "description": "Basic healthcare document samples", "tags": ["healthcare", "demo"]},
                {"name": "General Business", "description": "General business document samples", "tags": ["business", "demo"]},
                {"name": "PII Testing", "description": "PII detection and scrubbing test documents", "tags": ["pii", "demo"]}
            ]

        created_jars = []
        for jar_config in jar_configs:
            jar_id = self.create_honey_jar(
                name=jar_config["name"],
                description=jar_config["description"],
                jar_type="public",  # Demo jars are public
                tags=jar_config["tags"]
            )

            if jar_id:
                created_jars.append({
                    'id': jar_id,
                    'name': jar_config["name"],
                    'description': jar_config["description"],
                    'tags': jar_config["tags"]
                })
                # Small delay to avoid overwhelming the knowledge service
                time.sleep(0.5)

        return created_jars

    def get_document(self, honey_jar_id: str, document_id: str, db):
        """Get a specific document from a honey jar"""
        try:
            from app.models.document_models import Document
            import os

            document = db.query(Document).filter(
                Document.id == document_id,
                Document.honey_jar_id == honey_jar_id
            ).first()

            if not document:
                return None

            # Check if file exists
            file_exists = False
            if document.file_path:
                file_exists = os.path.exists(document.file_path)

            return {
                'id': str(document.id),
                'filename': document.filename,
                'file_path': document.file_path,
                'file_exists': file_exists,
                'size_bytes': document.size_bytes,
                'upload_date': document.created_at.isoformat() if document.created_at else None
            }
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None

    def get_document_preview(self, honey_jar_id: str, document_id: str, db, max_size=10240):
        """Get a preview of document content (first 10KB)"""
        try:
            from app.models.document_models import Document
            import os

            document = db.query(Document).filter(
                Document.id == document_id,
                Document.honey_jar_id == honey_jar_id
            ).first()

            if not document:
                return None

            # If file doesn't exist, return demo content based on filename
            if not document.file_path or not os.path.exists(document.file_path):
                logger.warning(f"File not found: {document.file_path}. Generating demo content.")

                # Generate demo content based on document type
                if 'patient' in document.filename.lower() and 'intake' in document.filename.lower():
                    return self._generate_patient_intake_demo(document.filename)
                elif 'lab' in document.filename.lower():
                    return self._generate_lab_result_demo(document.filename)
                elif 'prescription' in document.filename.lower():
                    return self._generate_prescription_demo(document.filename)
                else:
                    return f"""[Demo Content for {document.filename}]

This is demonstration content for the document: {document.filename}
Document ID: {document.id}
Content Type: {document.content_type}

In a production environment, this would contain the actual document content.
The file would be stored at: {document.file_path}

This demo content is being shown because the actual file was not created during the demo setup process.
"""

            # Read actual file if it exists
            with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_size)

            return content
        except Exception as e:
            logger.error(f"Error getting document preview: {str(e)}")
            return None

    def _generate_patient_intake_demo(self, filename):
        """Generate demo patient intake form content"""
        import random
        patient_num = filename.split('_')[-1].split('.')[0] if '_' in filename else str(random.randint(1, 999))
        return f"""PATIENT INTAKE FORM #{patient_num}
================================

Date: 2025-09-25
MRN: PAT-{patient_num.zfill(6)}

PATIENT INFORMATION:
- Name: [REDACTED for DEMO]
- Date of Birth: [REDACTED]
- SSN: XXX-XX-{patient_num.zfill(4)}
- Phone: 555-{random.randint(1000,9999)}
- Email: patient{patient_num}@demo.example

CHIEF COMPLAINT:
Patient presents with routine checkup requirements.

MEDICAL HISTORY:
- Hypertension (controlled)
- Type 2 Diabetes (managed with medication)
- Previous surgeries: Appendectomy (2015)

CURRENT MEDICATIONS:
- Metformin 500mg twice daily
- Lisinopril 10mg once daily
- Aspirin 81mg once daily

ALLERGIES:
- Penicillin (rash)
- Shellfish (anaphylaxis)

INSURANCE INFORMATION:
- Provider: Demo Health Insurance
- Policy #: DHI-{patient_num.zfill(8)}
- Group #: GRP-12345

[This is demonstration content for HIPAA-compliant document handling]
"""

    def _generate_lab_result_demo(self, filename):
        """Generate demo lab result content"""
        import random
        lab_num = filename.split('_')[-1].split('.')[0] if '_' in filename else str(random.randint(1, 999))
        return f"""LABORATORY RESULTS REPORT
=========================

Lab Order #: LAB-{lab_num.zfill(8)}
Date Collected: 2025-09-24
Date Reported: 2025-09-25

PATIENT: [DEMO PATIENT]
MRN: PAT-{lab_num.zfill(6)}

COMPLETE BLOOD COUNT (CBC):
- WBC: {random.randint(45, 110)/10:.1f} K/uL (4.5-11.0)
- RBC: {random.randint(42, 56)/10:.2f} M/uL (4.2-5.6)
- Hemoglobin: {random.randint(120, 160)/10:.1f} g/dL (12.0-16.0)
- Hematocrit: {random.randint(36, 46):.1f}% (36-46)
- Platelets: {random.randint(150, 400)} K/uL (150-400)

BASIC METABOLIC PANEL:
- Glucose: {random.randint(70, 110)} mg/dL (70-100)
- BUN: {random.randint(7, 25)} mg/dL (7-25)
- Creatinine: {random.randint(6, 13)/10:.1f} mg/dL (0.6-1.3)
- Sodium: {random.randint(136, 145)} mEq/L (136-145)
- Potassium: {random.randint(35, 50)/10:.1f} mEq/L (3.5-5.0)
- Chloride: {random.randint(98, 107)} mEq/L (98-107)

PHYSICIAN: Dr. Demo Physician
License #: MD-123456

[This is demonstration lab result content for healthcare compliance testing]
"""

    def _generate_prescription_demo(self, filename):
        """Generate demo prescription content"""
        import random
        rx_num = filename.split('_')[-1].split('.')[0] if '_' in filename else str(random.randint(1, 999))
        return f"""PRESCRIPTION FORM
==================

Rx #: RX-{rx_num.zfill(10)}
Date: 2025-09-25

PATIENT INFORMATION:
Name: [DEMO PATIENT]
DOB: [REDACTED]
Address: 123 Demo Street, Demo City, ST 12345

PRESCRIBER:
Dr. Demo Physician
DEA #: BD1234567
NPI: 1234567890
License #: MD-123456

MEDICATION:
℞ Metformin HCl 500mg
Sig: Take 1 tablet by mouth twice daily with meals
Quantity: #60 (sixty)
Refills: 5

Generic Substitution Permitted: ✓ Yes ☐ No

PHARMACY NOTES:
- Check for drug interactions
- Counsel patient on proper administration
- Monitor blood glucose levels

[This is demonstration prescription content with DEA number for compliance testing]
"""

# Singleton instance for reuse
_honey_jar_service = None

def get_honey_jar_service() -> HoneyJarService:
    """Get singleton honey jar service instance"""
    global _honey_jar_service
    if _honey_jar_service is None:
        _honey_jar_service = HoneyJarService()
    return _honey_jar_service