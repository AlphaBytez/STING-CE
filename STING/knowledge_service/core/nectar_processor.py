#!/usr/bin/env python3
"""
Nectar Processor - Document Processing Pipeline
Extracts and processes content from various document formats for Honey Jar storage
"""

import logging
from typing import List, Dict, Any, Optional
import io
import tempfile
import os
from fastapi import UploadFile
import PyPDF2
import docx
import magic
from bs4 import BeautifulSoup
import markdown
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import re

logger = logging.getLogger(__name__)

class NectarProcessor:
    """Processes documents to extract and chunk content for knowledge storage"""
    
    def __init__(self):
        self.supported_formats = {
            'application/pdf': self._extract_pdf,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._extract_docx,
            'text/plain': self._extract_text,
            'text/markdown': self._extract_markdown,
            'text/html': self._extract_html,
            'application/json': self._extract_json
        }
        
        # Download NLTK data if not present
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt')
    
    async def extract_text(self, file: UploadFile) -> str:
        """Extract text content from uploaded file"""
        try:
            # Read file content
            content = await file.read()
            
            # Detect MIME type
            mime_type = magic.from_buffer(content, mime=True)
            logger.info(f"Processing file {file.filename} with MIME type: {mime_type}")
            
            # Check if we support this format
            if mime_type not in self.supported_formats:
                # Fallback to filename extension
                ext = os.path.splitext(file.filename)[1].lower()
                ext_mime_type = self._get_mime_from_extension(ext)
                if ext_mime_type in self.supported_formats:
                    logger.info(f"Using MIME type from extension: {ext_mime_type} (detected was: {mime_type})")
                    mime_type = ext_mime_type
            
            if mime_type not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {mime_type}")
            
            # Extract text using appropriate method
            extractor = self.supported_formats[mime_type]
            text = await extractor(content, file.filename)
            
            # Clean and normalize text
            cleaned_text = self._clean_text(text)
            
            logger.info(f"Extracted {len(cleaned_text)} characters from {file.filename}")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Failed to extract text from {file.filename}: {e}")
            raise
    
    async def chunk_content(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 200,
        strategy: str = "sentence"
    ) -> List[str]:
        """Split content into overlapping chunks for embedding"""
        try:
            if strategy == "sentence":
                chunks = self._chunk_by_sentences(content, chunk_size, overlap)
            elif strategy == "paragraph":
                chunks = self._chunk_by_paragraphs(content, chunk_size, overlap)
            else:
                chunks = self._chunk_by_characters(content, chunk_size, overlap)
            
            # Filter out very small chunks
            chunks = [chunk for chunk in chunks if len(chunk.strip()) > 50]
            
            logger.info(f"Created {len(chunks)} chunks using {strategy} strategy")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk content: {e}")
            raise
    
    def _get_mime_from_extension(self, ext: str) -> str:
        """Get MIME type from file extension"""
        extension_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json'
        }
        return extension_map.get(ext, 'text/plain')
    
    async def _extract_pdf(self, content: bytes, filename: str) -> str:
        """Extract text from PDF files"""
        try:
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num} in {filename}: {e}")
                    continue
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Failed to extract PDF content: {e}")
            raise
    
    async def _extract_docx(self, content: bytes, filename: str) -> str:
        """Extract text from DOCX files"""
        try:
            with tempfile.NamedTemporaryFile() as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                doc = docx.Document(tmp_file.name)
                paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                
                return "\n\n".join(paragraphs)
                
        except Exception as e:
            logger.error(f"Failed to extract DOCX content: {e}")
            raise
    
    async def _extract_text(self, content: bytes, filename: str) -> str:
        """Extract text from plain text files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text = content.decode(encoding)
                    logger.debug(f"Successfully decoded {filename} with {encoding} encoding")
                    return text
                except UnicodeDecodeError:
                    continue
            
            # If all fail, use utf-8 with error handling
            text = content.decode('utf-8', errors='replace')
            logger.warning(f"Had to use utf-8 with error replacement for {filename}")
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract text content: {e}")
            raise
    
    async def _extract_markdown(self, content: bytes, filename: str) -> str:
        """Extract text from Markdown files"""
        try:
            md_content = content.decode('utf-8')
            
            # Convert markdown to HTML then extract text
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, 'html.parser')
            
            return soup.get_text(separator='\n', strip=True)
            
        except Exception as e:
            logger.error(f"Failed to extract Markdown content: {e}")
            raise
    
    async def _extract_html(self, content: bytes, filename: str) -> str:
        """Extract text from HTML files"""
        try:
            html_content = content.decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n', strip=True)
            
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract HTML content: {e}")
            raise
    
    async def _extract_json(self, content: bytes, filename: str) -> str:
        """Extract text from JSON files"""
        try:
            import json
            
            json_content = json.loads(content.decode('utf-8'))
            
            # Convert JSON to readable text
            text_parts = []
            self._json_to_text(json_content, text_parts)
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Failed to extract JSON content: {e}")
            raise
    
    def _json_to_text(self, obj: Any, text_parts: List[str], prefix: str = "") -> None:
        """Recursively convert JSON to text"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    text_parts.append(f"{prefix}{key}:")
                    self._json_to_text(value, text_parts, prefix + "  ")
                else:
                    text_parts.append(f"{prefix}{key}: {value}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    text_parts.append(f"{prefix}Item {i+1}:")
                    self._json_to_text(item, text_parts, prefix + "  ")
                else:
                    text_parts.append(f"{prefix}- {item}")
        else:
            text_parts.append(f"{prefix}{obj}")
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Split into lines first to preserve structure
        lines = text.split('\n')
        
        # Clean each line
        cleaned_lines = []
        for line in lines:
            # Remove excessive whitespace within lines
            cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
            # Skip very long lines (likely data/code)
            if len(cleaned_line) < 1000:
                cleaned_lines.append(cleaned_line)
        
        # Join back and strip
        return '\n'.join(cleaned_lines).strip()
    
    def _chunk_by_sentences(self, content: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk content by sentences while respecting size limits"""
        sentences = sent_tokenize(content)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # If adding this sentence would exceed chunk size, finalize current chunk
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Start new chunk with overlap
                overlap_sentences = []
                overlap_size = 0
                for prev_sentence in reversed(current_chunk):
                    if overlap_size + len(prev_sentence) <= overlap:
                        overlap_sentences.insert(0, prev_sentence)
                        overlap_size += len(prev_sentence)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_size = overlap_size
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _chunk_by_paragraphs(self, content: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk content by paragraphs"""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        return self._chunk_by_units(paragraphs, chunk_size, overlap)
    
    def _chunk_by_characters(self, content: str, chunk_size: int, overlap: int) -> List[str]:
        """Chunk content by character count"""
        chunks = []
        start = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk = content[start:end]
            chunks.append(chunk)
            start = end - overlap
            
            if start >= len(content):
                break
        
        return chunks
    
    def _chunk_by_units(self, units: List[str], chunk_size: int, overlap: int) -> List[str]:
        """Generic chunking by units (sentences, paragraphs, etc.)"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for unit in units:
            unit_size = len(unit)
            
            if current_size + unit_size > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                
                # Overlap logic
                overlap_units = []
                overlap_size = 0
                for prev_unit in reversed(current_chunk):
                    if overlap_size + len(prev_unit) <= overlap:
                        overlap_units.insert(0, prev_unit)
                        overlap_size += len(prev_unit)
                    else:
                        break
                
                current_chunk = overlap_units
                current_size = overlap_size
            
            current_chunk.append(unit)
            current_size += unit_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks