"""
Streaming Response Processor for Real-time PII Deserialization
"""
import asyncio
import re
from typing import AsyncGenerator, Dict, Optional, Set
from collections import deque
import logging

logger = logging.getLogger(__name__)

class StreamingPIIProcessor:
    """
    Process LLM responses in streaming fashion with real-time PII deserialization.
    Buffers partial tokens at chunk boundaries for accurate replacement.
    """

    def __init__(self, cache_manager, buffer_size: int = 256):
        self.cache_manager = cache_manager
        self.buffer_size = buffer_size
        self.token_pattern = re.compile(r'\$[A-Za-z]+\d+_[a-z_]+_[a-f0-9]{4}')
        self.partial_token_pattern = re.compile(r'\$[A-Za-z0-9_]*$')

    async def process_stream(
        self,
        response_stream: AsyncGenerator[str, None],
        conversation_id: str,
        pii_mapping: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process streaming response with real-time PII deserialization.

        Args:
            response_stream: Async generator of response chunks
            conversation_id: Conversation ID for PII lookup
            pii_mapping: Pre-fetched PII mapping (optional)

        Yields:
            Deserialized response chunks
        """
        # Pre-fetch PII mapping if not provided
        if pii_mapping is None:
            pii_mapping = await self._get_pii_mapping(conversation_id)

        # Buffer for handling tokens split across chunks
        buffer = ""
        processed_tokens: Set[str] = set()

        async for chunk in response_stream:
            # Combine buffer with new chunk
            combined = buffer + chunk

            # Find complete tokens in combined text
            tokens = self.token_pattern.findall(combined)

            # Check if chunk ends with a partial token
            partial_match = self.partial_token_pattern.search(combined)
            if partial_match and partial_match.end() == len(combined):
                # Keep partial token in buffer for next iteration
                buffer = partial_match.group()
                process_text = combined[:partial_match.start()]
            else:
                buffer = ""
                process_text = combined

            # Deserialize complete tokens
            for token in tokens:
                if token not in processed_tokens and token in pii_mapping:
                    process_text = process_text.replace(token, pii_mapping[token])
                    processed_tokens.add(token)

            # Yield processed chunk if not empty
            if process_text and not self.partial_token_pattern.fullmatch(process_text):
                yield process_text

        # Process any remaining buffer
        if buffer:
            for token in self.token_pattern.findall(buffer):
                if token in pii_mapping:
                    buffer = buffer.replace(token, pii_mapping[token])
            yield buffer

    async def process_chunked_response(
        self,
        response_chunks: list[str],
        conversation_id: str,
        chunk_size: int = 64
    ) -> AsyncGenerator[str, None]:
        """
        Process response in chunks for better perceived performance.

        Args:
            response_chunks: List of response chunks
            conversation_id: Conversation ID for PII lookup
            chunk_size: Size of chunks to yield

        Yields:
            Deserialized response chunks
        """
        # Pre-fetch PII mapping
        pii_mapping = await self._get_pii_mapping(conversation_id)

        # Process chunks with buffering
        buffer = deque()
        buffer_length = 0

        for chunk in response_chunks:
            # Deserialize tokens in chunk
            for token in self.token_pattern.findall(chunk):
                if token in pii_mapping:
                    chunk = chunk.replace(token, pii_mapping[token])

            # Add to buffer
            buffer.append(chunk)
            buffer_length += len(chunk)

            # Yield when buffer reaches chunk_size
            while buffer_length >= chunk_size:
                output = ""
                while buffer and len(output) < chunk_size:
                    next_chunk = buffer.popleft()
                    output += next_chunk
                    buffer_length -= len(next_chunk)

                # Handle overshoot
                if len(output) > chunk_size:
                    excess = output[chunk_size:]
                    output = output[:chunk_size]
                    buffer.appendleft(excess)
                    buffer_length += len(excess)

                yield output

        # Yield remaining buffer
        while buffer:
            yield buffer.popleft()

    async def _get_pii_mapping(self, conversation_id: str) -> Dict[str, str]:
        """Get PII mapping with error handling"""
        try:
            mapping = await self.cache_manager.get_pii_mapping(conversation_id)
            if mapping:
                logger.info(f"Loaded {len(mapping)} PII mappings for conversation {conversation_id}")
                return mapping
        except Exception as e:
            logger.error(f"Failed to load PII mapping: {e}")

        logger.warning(f"No PII mapping found for conversation {conversation_id}")
        return {}

    def create_buffered_processor(self, conversation_id: str, pii_mapping: Dict[str, str]):
        """
        Create a buffered processor for optimal performance.

        Returns a processor function that can be used with response streams.
        """
        class BufferedProcessor:
            def __init__(self, mapping: Dict[str, str], buffer_size: int = 256):
                self.mapping = mapping
                self.buffer = ""
                self.buffer_size = buffer_size
                self.token_pattern = re.compile(r'\$[A-Za-z]+\d+_[a-z_]+_[a-f0-9]{4}')
                self.partial_pattern = re.compile(r'\$[A-Za-z0-9_]*$')

            def process_chunk(self, chunk: str) -> Optional[str]:
                """Process a single chunk with buffering"""
                self.buffer += chunk

                # Only process if buffer is large enough or contains complete tokens
                if len(self.buffer) < self.buffer_size:
                    # Check for complete tokens even in small buffer
                    if not self.token_pattern.search(self.buffer):
                        return None

                # Extract processable part
                process_text = self.buffer

                # Check for partial token at end
                partial = self.partial_pattern.search(process_text)
                if partial and partial.end() == len(process_text):
                    # Keep partial token in buffer
                    self.buffer = partial.group()
                    process_text = process_text[:partial.start()]
                else:
                    self.buffer = ""

                # Deserialize tokens
                for token, value in self.mapping.items():
                    process_text = process_text.replace(token, value)

                return process_text if process_text else None

            def flush(self) -> Optional[str]:
                """Flush remaining buffer"""
                if not self.buffer:
                    return None

                result = self.buffer
                for token, value in self.mapping.items():
                    result = result.replace(token, value)

                self.buffer = ""
                return result

        return BufferedProcessor(pii_mapping)

    async def warm_cache(self, conversation_ids: list[str]):
        """
        Pre-warm cache for multiple conversations to improve response time.

        Args:
            conversation_ids: List of conversation IDs to pre-load
        """
        tasks = [self._get_pii_mapping(conv_id) for conv_id in conversation_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if isinstance(r, dict) and r)
        logger.info(f"Pre-warmed cache for {success_count}/{len(conversation_ids)} conversations")