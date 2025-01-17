import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Optional
from pathlib import Path
from dataclasses import dataclass
from core_agent.aws import AWSS3Client
from core.utils import load_credential


@dataclass
class ChromaServiceConfig:
    """Configuration settings for ChromaService."""
    embedding_model: str = "text-embedding-3-large"
    collection_name: str = "collection_1"
    persist_directory_base: Path = Path(".tmp")
    aws_s3_bucket_name: str = "example.com-assets"
    aws_s3_base_prefix: str = "threads"

    def get_persist_directory(self, thread_id: str) -> Path:
        """Get the persistence directory for a specific thread."""
        return self.persist_directory_base / thread_id / "chroma_langchain_db"
    
    def get_s3_prefix(self, thread_id: str) -> str:
        """Get the S3 prefix for a specific thread."""
        return f"{self.aws_s3_base_prefix}/{thread_id}"


class ChromaService:
    """
    Service for managing Chroma vector stores for different threads.
    """
    def __init__(self, config: Optional[ChromaServiceConfig] = None):
        """Initialize ChromaService with optional configuration."""
        self.config = config or ChromaServiceConfig()
        self.aws_s3_client = AWSS3Client()

    def get_or_create_vector_store(self, thread_id: str):
        """Get or create a vector store for the given thread ID."""
        embeddings = OpenAIEmbeddings(
            model=self.config.embedding_model,
            openai_api_key=load_credential("OPENAI_API_KEY"),
        )
        persist_directory = str(self.config.get_persist_directory(thread_id))
        chroma = Chroma(
            collection_name=self.config.collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )
        return chroma
    
    def check_thread_exists(self, thread_id: str) -> bool:
        """
        Check if a thread exists in S3 by looking for its Chroma directory.
        
        Args:
            thread_id (str): The ID of the thread to check
            
        Returns:
            bool: True if the thread exists in S3, False otherwise
        """
        try:
            s3_prefix = self.config.get_s3_prefix(thread_id)
            
            # List objects with the thread's prefix to see if any exist
            objects = self.aws_s3_client.get_s3().list_objects_v2(
                Bucket=self.config.aws_s3_bucket_name,
                Prefix=s3_prefix
            )
            
            # If there are any objects with this prefix, the thread exists
            return objects.get("KeyCount", 0) > 0
            
        except Exception as e:
            raise ValueError(f"Error checking thread existence in S3: {str(e)}") from e
    
    def _upload_directory_to_s3(self, local_dir: str, thread_id: str):
        """
        Upload all files in a directory to S3, maintaining the directory structure.
        
        Args:
            local_dir (str): Local directory path to upload
            thread_id (str): Thread ID to use as the base S3 prefix
        """
        base_path = Path(local_dir)
        s3_base_prefix = self.config.get_s3_prefix(thread_id)
        
        for file_path in base_path.rglob('*'):
            if file_path.is_file():
                # Calculate relative path from base directory
                relative_path = file_path.relative_to(base_path)
                # Construct S3 key with thread_id as prefix
                s3_key = f"{s3_base_prefix}/{relative_path}"
                
                try:
                    self.aws_s3_client.upload_s3_file(
                        bucket_name=self.config.aws_s3_bucket_name,
                        local_file_path=str(file_path),
                        s3_key=s3_key
                    )
                except Exception as e:
                    raise ValueError(f"Error uploading file to S3: {str(e)}") from e

    def upload_and_vectorize_pdf_for_thread(self, thread_id: str, pdf_path: str):
        """Upload a PDF file to S3 and add it to the vector store for the given thread."""
        try:
            # Load the PDF
            loader = PyPDFLoader(pdf_path)
            new_docs = loader.load()

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=1000,
                chunk_overlap=200
            )
            new_splits = text_splitter.split_documents(new_docs)

            # Get or create vector store and add documents
            vector_store = self.get_or_create_vector_store(thread_id)
            vector_store.add_documents(new_splits)
            
            # Upload the entire Chroma directory structure to S3
            persist_directory = str(self.config.get_persist_directory(thread_id))
            self._upload_directory_to_s3(persist_directory, thread_id)
            
        except Exception as e:
            raise Exception(f"Error adding PDF to vectorstore: {str(e)}") from e