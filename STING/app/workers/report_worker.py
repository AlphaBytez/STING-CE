"""
Report Worker for STING-CE
Processes report generation jobs from the queue.
"""

import os
import sys
import logging
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
from io import BytesIO
import uuid

# Add app to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.report_service import get_report_service
from app.services.file_service import get_file_service
from app.services.hive_scrambler import HiveScrambler
from app.models.report_models import Report, ReportTemplate, get_report_by_id
from app.database import get_db_session

# Report generators
from app.workers.report_generators import (
    HoneyJarSummaryGenerator,
    UserActivityAuditGenerator,
    DocumentProcessingReportGenerator,
    BeeChatAnalyticsGenerator,
    EncryptionStatusReportGenerator,
    StorageUtilizationReportGenerator,
    HealthcareComplianceGenerator
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReportWorker:
    """Worker for processing report generation jobs"""
    
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.report_service = get_report_service()
        self.file_service = get_file_service()
        self.scrambler = HiveScrambler()
        self.is_running = False
        self.current_job = None
        
        # Map template names to generator classes
        self.generators = {
            'honey_jar_summary': HoneyJarSummaryGenerator,
            'user_activity_audit': UserActivityAuditGenerator,
            'document_processing_report': DocumentProcessingReportGenerator,
            'bee_chat_analytics': BeeChatAnalyticsGenerator,
            'encryption_status_report': EncryptionStatusReportGenerator,
            'storage_utilization_report': StorageUtilizationReportGenerator,
            'healthcare_compliance_report': HealthcareComplianceGenerator
        }
        
        logger.info(f"Report worker {self.worker_id} initialized")
    
    async def start(self):
        """Start the worker loop"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} started")
        
        while self.is_running:
            try:
                # Check for jobs
                job = self.report_service.get_next_job(self.worker_id)
                
                if job:
                    self.current_job = job
                    await self.process_job(job)
                    self.current_job = None
                else:
                    # No jobs available, wait before checking again
                    await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(10)
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping worker {self.worker_id}")
        self.is_running = False
        
        # Wait for current job to complete
        if self.current_job:
            logger.info(f"Waiting for current job to complete: {self.current_job['report_id']}")
            # TODO: Implement graceful shutdown with timeout
    
    async def process_job(self, job: Dict[str, Any]):
        """Process a single report generation job"""
        report_id = job['report_id']
        logger.info(f"Processing report {report_id}")
        
        try:
            # Get report and template details
            with get_db_session() as session:
                report = get_report_by_id(session, report_id)
                if not report:
                    raise Exception(f"Report {report_id} not found")

                # Access template within the session to avoid detached instance
                template = report.template
                if not template:
                    raise Exception(f"Template not found for report {report_id}")

                # Store template and report info for use outside session
                template_name = template.name
                template_display_name = template.display_name
                template_config = template.template_config or {}
                report_title = report.title
                report_output_format = report.output_format or 'pdf'
            
            # Update progress
            self.report_service.update_progress(report_id, 10, "Starting report generation")
            
            # Get the appropriate generator
            generator_class = self.generators.get(template_name)
            if not generator_class:
                raise Exception(f"No generator found for template: {template_name}")

            # Initialize generator with parameters
            generator = generator_class(
                report_id=report_id,
                template_config=template_config,
                parameters=job.get('parameters', {}),
                user_id=job['user_id']
            )
            
            # Generate report data
            self.report_service.update_progress(report_id, 30, "Collecting data")
            report_data = await generator.generate()
            
            # Generate output file
            self.report_service.update_progress(report_id, 70, "Creating report file")
            file_data = await self.create_output_file(
                report_data,
                report_output_format,
                template_name,
                report_title
            )
            
            # Save file to storage
            self.report_service.update_progress(report_id, 90, "Saving report")
            file_metadata = self.file_service.upload_file(
                file_data=file_data['content'],
                filename=file_data['filename'],
                file_type='report',
                user_id=job['user_id'],
                metadata={
                    'type': 'report',
                    'report_id': report_id,
                    'template': template_name,
                    'format': report_output_format
                }
            )
            
            if not file_metadata or not file_metadata.get('file_id'):
                raise Exception("Failed to save report file")
            
            # Complete the job
            self.report_service.complete_job(
                report_id,
                file_metadata['file_id'],
                result_summary={
                    'records_processed': report_data.get('record_count', 0),
                    'data_points': report_data.get('data_points', 0),
                    'pii_scrubbed': report_data.get('pii_scrubbed', False),
                    'generation_time': report_data.get('generation_time', 0)
                }
            )
            
            logger.info(f"Successfully completed report {report_id}")
            
        except Exception as e:
            logger.error(f"Failed to process report {report_id}: {e}")
            self.report_service.fail_job(report_id, str(e), retry=True)
    
    async def create_output_file(self, report_data: Dict[str, Any], 
                                output_format: str, template_name: str,
                                report_title: str) -> Dict[str, Any]:
        """Create the output file in the requested format"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in report_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}_{timestamp}.{output_format}"
        
        if output_format == 'csv':
            # Convert data to CSV
            df = pd.DataFrame(report_data.get('data', []))
            buffer = BytesIO()
            df.to_csv(buffer, index=False)
            content = buffer.getvalue()
            
        elif output_format == 'xlsx':
            # Convert data to Excel with multiple sheets if needed
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Main data sheet
                if 'data' in report_data:
                    df = pd.DataFrame(report_data['data'])
                    df.to_excel(writer, sheet_name='Data', index=False)
                
                # Summary sheet
                if 'summary' in report_data:
                    summary_df = pd.DataFrame([report_data['summary']])
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Charts data if available
                if 'charts' in report_data:
                    for chart_name, chart_data in report_data['charts'].items():
                        chart_df = pd.DataFrame(chart_data)
                        sheet_name = chart_name[:31]  # Excel sheet name limit
                        chart_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            content = buffer.getvalue()
            
        elif output_format == 'pdf':
            # Professional STING-branded PDF generation
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.graphics.shapes import Drawing, Rect

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                leftMargin=0.75*inch,
                rightMargin=0.75*inch,
                topMargin=1*inch,
                bottomMargin=1*inch
            )
            story = []
            styles = getSampleStyleSheet()

            # STING Professional Color Palette
            STING_BLUE = colors.HexColor('#1e40af')      # Professional blue
            STING_DARK = colors.HexColor('#1f2937')      # Dark gray
            STING_ACCENT = colors.HexColor('#f59e0b')    # Honey accent (subtle)
            STING_LIGHT = colors.HexColor('#f8fafc')     # Light background

            # Header Section with STING Branding
            header_style = ParagraphStyle(
                'STINGHeader',
                parent=styles['Normal'],
                fontSize=10,
                textColor=STING_BLUE,
                alignment=2  # Right align
            )
            story.append(Paragraph("Generated by <b>STING Platform</b>", header_style))
            story.append(Spacer(1, 0.1*inch))

            # Branded Title Section
            title_style = ParagraphStyle(
                'STINGTitle',
                parent=styles['Title'],
                fontSize=28,
                textColor=STING_BLUE,
                spaceAfter=0.2*inch,
                alignment=1  # Center align
            )
            story.append(Paragraph(f"<b>{report_title}</b>", title_style))

            # Professional subtitle
            subtitle_style = ParagraphStyle(
                'STINGSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor=STING_DARK,
                alignment=1,  # Center align
                spaceAfter=0.3*inch
            )
            story.append(Paragraph(f"<i>{template_name}</i>", subtitle_style))

            # Professional divider line
            divider = Drawing(400, 1)
            divider.add(Rect(0, 0, 400, 1, fillColor=STING_BLUE, strokeColor=STING_BLUE))
            story.append(divider)
            story.append(Spacer(1, 0.3*inch))
            
            # Metadata
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"Template: {template_name}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Professional Summary Section
            if 'summary' in report_data:
                # Section header with STING styling
                summary_header_style = ParagraphStyle(
                    'STINGSectionHeader',
                    parent=styles['Heading2'],
                    fontSize=16,
                    textColor=STING_BLUE,
                    spaceBefore=0.2*inch,
                    spaceAfter=0.1*inch,
                    borderWidth=0,
                    borderColor=STING_BLUE,
                    borderPadding=5
                )
                story.append(Paragraph("📊 Executive Summary", summary_header_style))

                # Summary metrics in professional format
                summary_style = ParagraphStyle(
                    'STINGSummary',
                    parent=styles['Normal'],
                    fontSize=11,
                    textColor=STING_DARK,
                    leftIndent=0.2*inch,
                    spaceAfter=4
                )
                for key, value in report_data['summary'].items():
                    clean_key = key.replace('_', ' ').title()
                    story.append(Paragraph(f"<b style='color: {STING_BLUE}'>{clean_key}:</b> {value}", summary_style))
                story.append(Spacer(1, 0.4*inch))

            # Professional Data Table
            if 'data' in report_data and report_data['data']:
                # Data section header
                data_header_style = ParagraphStyle(
                    'STINGDataHeader',
                    parent=styles['Heading2'],
                    fontSize=16,
                    textColor=STING_BLUE,
                    spaceAfter=0.2*inch
                )
                story.append(Paragraph("📈 Detailed Analysis", data_header_style))

                # Convert to table format
                data_rows = report_data['data'][:50]  # Limit for PDF
                if data_rows:
                    # Headers
                    headers = [h.replace('_', ' ').title() for h in data_rows[0].keys()]
                    table_data = [headers]

                    # Data rows
                    for row in data_rows:
                        table_data.append([str(row.get(h, '')) for h in data_rows[0].keys()])

                    # Professional table with STING branding
                    t = Table(table_data, repeatRows=1)
                    t.setStyle(TableStyle([
                        # Header styling (STING blue theme)
                        ('BACKGROUND', (0, 0), (-1, 0), STING_BLUE),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

                        # Data rows styling (alternating colors)
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, STING_LIGHT]),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('TOPPADDING', (0, 1), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

                        # Professional grid
                        ('GRID', (0, 0), (-1, -1), 0.5, STING_DARK),
                        ('LINEBELOW', (0, 0), (-1, 0), 2, STING_BLUE),
                    ]))
                    story.append(t)

                    if len(report_data['data']) > 50:
                        story.append(Spacer(1, 0.3*inch))
                        note_style = ParagraphStyle(
                            'STINGNote',
                            parent=styles['Italic'],
                            fontSize=9,
                            textColor=STING_DARK,
                            alignment=1  # Center
                        )
                        story.append(Paragraph(
                            f"📋 Showing first 50 of {len(report_data['data'])} records. "
                            f"Download complete report as CSV or Excel for full dataset.",
                            note_style
                        ))
            
            # Professional Footer
            story.append(Spacer(1, 0.5*inch))

            # Footer divider
            footer_divider = Drawing(400, 1)
            footer_divider.add(Rect(0, 0, 400, 1, fillColor=STING_BLUE, strokeColor=STING_BLUE))
            story.append(footer_divider)
            story.append(Spacer(1, 0.2*inch))

            # STING footer branding
            footer_style = ParagraphStyle(
                'STINGFooter',
                parent=styles['Normal'],
                fontSize=9,
                textColor=STING_DARK,
                alignment=1  # Center align
            )
            generation_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            story.append(Paragraph(
                f"🐝 <b>STING Platform</b> • Generated on {generation_time} • "
                f"Secure Intelligence & Analytics",
                footer_style
            ))

            # Build PDF with STING branding
            doc.build(story)
            content = buffer.getvalue()
            
        else:
            # Default to JSON
            content = json.dumps(report_data, indent=2).encode()
            filename = filename.replace(f'.{output_format}', '.json')
        
        return {
            'content': content,
            'filename': filename,
            'mime_type': {
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'pdf': 'application/pdf',
                'json': 'application/json'
            }.get(output_format, 'application/octet-stream')
        }

# Worker entry point
async def main():
    """Main entry point for the worker"""
    worker = ReportWorker()
    
    try:
        # Start the worker
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        raise

if __name__ == '__main__':
    # Run the worker
    asyncio.run(main())