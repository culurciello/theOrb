from typing import Dict, Any
from pathlib import Path
import pandas as pd
import json
import mimetypes
from .base_pipeline import BasePipeline

class TablePipeline(BasePipeline):
    """
    Table processing pipeline:
    - convert table to JSON
    - send to database: [link to original file, JSON]
    """
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process table file according to the pipeline specification."""
        file_path = Path(file_path)
        
        # Convert table to JSON
        table_json = self.convert_table_to_json(str(file_path))
        
        # Generate summary description for embeddings
        summary = self.generate_table_summary(table_json, file_path.stem)
        
        # Generate embeddings for the summary
        embedding_list = self.get_sentence_embeddings([summary])

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            'link_to_original_file': str(file_path),
            'json_data': table_json,
            'summary': summary,
            'content': summary,  # Use summary as content for compatibility
            'chunks': [summary],  # Single chunk with the summary for compatibility
            'categories': ['table'],  # Default category
            'embedding_list': embedding_list,
            'file_type': 'table',
            'mime_type': mime_type,
            'metadata': {
                'file_extension': file_path.suffix,
                'row_count': len(table_json.get('data', [])),
                'column_count': len(table_json.get('columns', []))
            }
        }
    
    def convert_table_to_json(self, file_path: str) -> Dict[str, Any]:
        """Convert table file (CSV, Excel) to JSON format."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported table file type: {file_ext}")
            
            # Convert to JSON structure
            table_json = {
                'columns': df.columns.tolist(),
                'data': df.to_dict('records'),
                'shape': {
                    'rows': len(df),
                    'columns': len(df.columns)
                },
                'column_types': {col: str(dtype) for col, dtype in df.dtypes.items()}
            }
            
            return table_json
            
        except Exception as e:
            print(f"Error converting table to JSON: {e}")
            return {
                'error': str(e),
                'columns': [],
                'data': [],
                'shape': {'rows': 0, 'columns': 0}
            }
    
    def generate_table_summary(self, table_json: Dict[str, Any], filename: str) -> str:
        """Generate a summary description of the table for embeddings."""
        if 'error' in table_json:
            return f"Table '{filename}': Error processing file - {table_json['error']}"
        
        columns = table_json.get('columns', [])
        row_count = table_json.get('shape', {}).get('rows', 0)
        
        # Create summary with column names and basic stats
        column_list = ', '.join(columns[:10])  # First 10 columns
        if len(columns) > 10:
            column_list += f" and {len(columns) - 10} more columns"
        
        summary = f"Table '{filename}' contains {row_count} rows with columns: {column_list}."
        
        # Add sample data context if available
        if table_json.get('data'):
            sample_data = table_json['data'][:3]  # First 3 rows
            data_preview = "; ".join([
                f"{col}: {row.get(col, 'N/A')}" 
                for row in sample_data[:1] 
                for col in columns[:3]
            ])
            if data_preview:
                summary += f" Sample data: {data_preview}"
        
        return summary