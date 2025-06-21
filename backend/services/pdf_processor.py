import pdfplumber
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
import hashlib
from datetime import datetime

from models.document import DocumentChunk, DocumentMetadata, ProcessedDocument


class PDFProcessor:
    """Service for processing PDF documents into searchable chunks"""
    
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def process_pdf(self, file_path: str) -> ProcessedDocument:
        """Process a PDF file and return structured document data"""
        try:
            filename = Path(file_path).name
            chunks = []
            
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                tables = []
                
                # Extract text and tables from all pages
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    full_text += f"\n\n--- Strana {page_num + 1} ---\n\n" + page_text
                    
                    # Extract tables if present
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            table_text = self._format_table(table)
                            full_text += f"\n\nTabela:\n{table_text}\n"
            
            # Create chunks from the extracted text
            text_chunks = self._create_chunks(full_text)
            
            # Process each chunk
            for i, chunk_text in enumerate(text_chunks):
                metadata = self._extract_metadata(chunk_text, filename)
                
                chunk = DocumentChunk(
                    id=self._generate_chunk_id(filename, i),
                    text=chunk_text.strip(),
                    metadata=metadata,
                    created_at=datetime.now()
                )
                chunks.append(chunk)
            
            return ProcessedDocument(
                filename=filename,
                chunks=chunks,
                total_chunks=len(chunks),
                processing_status="success",
                processed_at=datetime.now()
            )
            
        except Exception as e:
            return ProcessedDocument(
                filename=Path(file_path).name,
                chunks=[],
                total_chunks=0,
                processing_status="error",
                error_message=str(e),
                processed_at=datetime.now()
            )
    
    def _create_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        # Split by sentences and paragraphs
        sentences = re.split(r'[.!?]\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk.split()) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # Start new chunk with overlap
                    overlap_words = current_chunk.split()[-self.chunk_overlap:]
                    current_chunk = " ".join(overlap_words) + " " + sentence
                else:
                    # Single sentence is too long, split it
                    words = sentence.split()
                    for i in range(0, len(words), self.chunk_size):
                        chunk_words = words[i:i + self.chunk_size]
                        chunks.append(" ".join(chunk_words))
                    current_chunk = ""
            else:
                current_chunk = potential_chunk
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks
    
    def _extract_metadata(self, text: str, filename: str) -> DocumentMetadata:
        """Extract metadata from chunk text"""
        text_lower = text.lower()
        
        # Category detection
        category = None
        if any(word in text_lower for word in ['hotel', 'smeštaj', 'apartman', 'vila']):
            category = "hotel"
        elif any(word in text_lower for word in ['restoran', 'kafana', 'bar', 'restoran']):
            category = "restaurant"
        elif any(word in text_lower for word in ['muzej', 'crkva', 'tvrđava', 'spomenik', 'galerija']):
            category = "attraction"
        elif any(word in text_lower for word in ['tura', 'izlet', 'putovanje', 'aranžman']):
            category = "tour"
        
        # Location detection
        location = self._extract_location(text_lower)
        
        # Price range detection
        price_range = self._extract_price_range(text)
        
        # Family friendly detection
        family_friendly = any(word in text_lower for word in [
            'porodica', 'deca', 'family', 'family-friendly', 'pogodno za decu'
        ])
        
        # Seasonal detection
        seasonal = self._extract_seasonal(text_lower)
        
        return DocumentMetadata(
            category=category,
            location=location,
            price_range=price_range,
            family_friendly=family_friendly,
            seasonal=seasonal,
            source_file=filename
        )
    
    def _extract_location(self, text: str) -> str:
        """Extract location from text"""
        # Major cities and regions
        locations = {
            'beograd': 'Beograd',
            'novi sad': 'Novi Sad',
            'niš': 'Niš',
            'kragujevac': 'Kragujevac',
            'rim': 'Rim',
            'rim ': 'Rim',
            'roma': 'Rim',
            'pariz': 'Pariz',
            'berlin': 'Berlin',
            'beč': 'Beč',
            'vienna': 'Beč',
            'prag': 'Prag',
            'budimpešta': 'Budimpešta',
            'istanbul': 'Istanbul',
            'atina': 'Atina',
            'solun': 'Solun',
            'barcelona': 'Barcelona',
            'madrid': 'Madrid',
            'london': 'London',
            'amsterdam': 'Amsterdam',
            'kopaonik': 'Kopaonik',
            'zlatibor': 'Zlatibor',
            'tara': 'Tara',
            'fruška gora': 'Fruška Gora'
        }
        
        for key, value in locations.items():
            if key in text:
                return value
        
        return None
    
    def _extract_price_range(self, text: str) -> str:
        """Extract price range from text based on prices mentioned"""
        # Extract all prices (€, $, RSD)
        price_pattern = r'(\d+(?:\.\d+)?)\s*(?:€|eur|usd|\$|rsd|din)'
        prices = re.findall(price_pattern, text.lower())
        
        if not prices:
            return None
        
        # Convert to float and find average
        numeric_prices = []
        for price in prices:
            try:
                numeric_prices.append(float(price))
            except ValueError:
                continue
        
        if not numeric_prices:
            return None
        
        avg_price = sum(numeric_prices) / len(numeric_prices)
        
        # Categorize based on average price (assumes EUR)
        if avg_price < 50:
            return "budget"
        elif avg_price < 150:
            return "moderate"
        elif avg_price < 300:
            return "expensive"
        else:
            return "luxury"
    
    def _extract_seasonal(self, text: str) -> str:
        """Extract seasonal information"""
        if any(word in text for word in ['leto', 'summer', 'jun', 'jul', 'avgust']):
            return "summer"
        elif any(word in text for word in ['zima', 'winter', 'decembar', 'januar', 'februar']):
            return "winter"
        elif any(word in text for word in ['proleće', 'spring', 'mart', 'april', 'maj']):
            return "spring"
        elif any(word in text for word in ['jesen', 'autumn', 'septembar', 'oktobar', 'novembar']):
            return "autumn"
        else:
            return "year_round"
    
    def _format_table(self, table: List[List[str]]) -> str:
        """Format extracted table data"""
        if not table:
            return ""
        
        formatted_rows = []
        for row in table:
            if row:  # Skip empty rows
                formatted_row = " | ".join(str(cell) if cell else "" for cell in row)
                formatted_rows.append(formatted_row)
        
        return "\n".join(formatted_rows)
    
    def _generate_chunk_id(self, filename: str, chunk_index: int) -> str:
        """Generate unique chunk ID"""
        content = f"{filename}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()[:12] 