#!/usr/bin/env python3
"""Simple report worker for testing"""

import os
import sys
import logging
import time
import json
from datetime import datetime

sys.path.insert(0, '/opt/sting-ce')

from app.services.report_service import get_report_service
from app.database import get_db_session
from app.models.report_models import Report, ReportStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_report(report_id: str):
    """Process a single report"""
    logger.info(f"Processing report {report_id}")
    
    with get_db_session() as session:
        report = session.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error(f"Report {report_id} not found")
            return
        
        # Update status to processing
        report.status = 'processing'
        report.started_at = datetime.utcnow()
        report.progress_percentage = 10
        session.commit()
        
        logger.info(f"Report {report_id} marked as processing")
        
        # Simulate report generation
        time.sleep(2)
        
        # For now, create a simple JSON result
        result_data = {
            "title": report.title,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_honey_jars": 2,
                "total_documents": 0,
                "total_size_mb": 0,
                "most_active_jar": "Sample Business Jar"
            },
            "details": "This is a test report. In a real implementation, this would contain actual honey jar data."
        }
        
        # Update progress
        report.progress_percentage = 80
        session.commit()
        
        # Save result as JSON for now (since we can't generate PDFs without proper data)
        report.status = 'completed'
        report.completed_at = datetime.utcnow()
        report.progress_percentage = 100
        report.result_summary = result_data
        session.commit()
        
        logger.info(f"Report {report_id} completed successfully")

def main():
    """Main worker loop"""
    logger.info("Starting simple report worker...")
    
    report_service = get_report_service()
    worker_id = "test-worker-001"
    
    while True:
        try:
            # Get next job from queue
            job = report_service.get_next_job(worker_id)
            
            if job:
                logger.info(f"Got job: {job['report_id']}")
                process_report(job['report_id'])
            else:
                logger.debug("No jobs in queue, waiting...")
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()