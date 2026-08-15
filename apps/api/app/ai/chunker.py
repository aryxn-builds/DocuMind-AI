import uuid
import re
from typing import List

from app.ai.models import NormalizedDocument, Chunk, BlockType


class Chunker:
    TARGET_CHUNK_CHARS = 800
    MAX_CHUNK_CHARS = 1200
    OVERLAP_SENTENCES = 2
    MIN_CHUNK_CHARS = 50

    def chunk(self, document: NormalizedDocument) -> List[Chunk]:
        chunks: List[Chunk] = []
        chunk_index = 0
        
        current_heading_prefix = ""
        current_text_buffer = ""
        current_block_ids = []
        current_bbox = None
        current_page = None
        current_section = []
        
        def commit_text_buffer():
            nonlocal chunk_index, current_text_buffer, current_block_ids, current_bbox, current_page, current_section
            if not current_text_buffer:
                return
                
            content = current_text_buffer.strip()
            
            if len(content) > self.TARGET_CHUNK_CHARS:
                # Split at sentence boundaries
                sentences = re.split(r'(?<=[.!?])\s+', content)
                
                temp_content = ""
                for i, sentence in enumerate(sentences):
                    if len(temp_content) + len(sentence) > self.TARGET_CHUNK_CHARS and len(temp_content) >= self.MIN_CHUNK_CHARS:
                        chunks.append(self._create_chunk(
                            document, chunk_index, BlockType.TEXT.value, temp_content.strip(),
                            current_page, current_section, current_bbox, current_block_ids
                        ))
                        chunk_index += 1
                        
                        # Overlap: keep last N sentences
                        overlap_sentences = sentences[max(0, i - self.OVERLAP_SENTENCES):i]
                        overlap = " ".join(overlap_sentences)
                        
                        prefix = current_heading_prefix if current_heading_prefix else ""
                        temp_content = prefix + overlap + " " + sentence if overlap else prefix + sentence
                    else:
                        temp_content += " " + sentence if temp_content else sentence
                
                if len(temp_content.strip()) >= self.MIN_CHUNK_CHARS:
                    chunks.append(self._create_chunk(
                        document, chunk_index, BlockType.TEXT.value, temp_content.strip(),
                        current_page, current_section, current_bbox, current_block_ids
                    ))
                    chunk_index += 1
            else:
                if len(content) >= self.MIN_CHUNK_CHARS:
                    chunks.append(self._create_chunk(
                        document, chunk_index, BlockType.TEXT.value, content,
                        current_page, current_section, current_bbox, current_block_ids
                    ))
                    chunk_index += 1

            current_text_buffer = ""
            current_block_ids = []
            
        for block in document.blocks:
            if block.block_type == BlockType.HEADING:
                commit_text_buffer()
                current_heading_prefix = block.content.strip() + "\n\n"
                
            elif block.block_type in (BlockType.TEXT, BlockType.LIST, BlockType.CAPTION):
                if current_text_buffer and len(current_text_buffer) + len(block.content) > self.TARGET_CHUNK_CHARS:
                    commit_text_buffer()
                    
                if not current_text_buffer:
                    current_text_buffer = current_heading_prefix
                    current_bbox = block.bbox
                    current_page = block.page_number
                    current_section = block.section_path
                
                current_text_buffer += block.content + " "
                current_block_ids.append(block.block_id)
                
            elif block.block_type == BlockType.TABLE:
                commit_text_buffer()
                content = current_heading_prefix + block.content.strip()
                chunks.append(self._create_chunk(
                    document, chunk_index, BlockType.TABLE.value, content,
                    block.page_number, block.section_path, block.bbox, [block.block_id],
                    table_data=block.table_data
                ))
                chunk_index += 1
                current_heading_prefix = ""
                
            elif block.block_type == BlockType.IMAGE:
                commit_text_buffer()
                content = block.content.strip()
                chunks.append(self._create_chunk(
                    document, chunk_index, BlockType.IMAGE.value, content,
                    block.page_number, block.section_path, block.bbox, [block.block_id]
                ))
                chunk_index += 1
                current_heading_prefix = ""
                
        commit_text_buffer()
        return chunks

    def _create_chunk(self, doc, index, ctype, content, page, section, bbox, source_ids, table_data=None) -> Chunk:
        # Enforce hard limit
        if len(content) > self.MAX_CHUNK_CHARS:
            content = content[:self.MAX_CHUNK_CHARS - 3] + "..."
            
        return Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc.document_id,
            user_id=doc.user_id,
            chunk_index=index,
            chunk_type=ctype,
            content=content,
            page_number=page,
            section_path=section.copy() if section else [],
            bbox=bbox,
            table_data=table_data,
            source_block_ids=source_ids.copy() if source_ids else [],
            content_preview=content[:200]
        )
