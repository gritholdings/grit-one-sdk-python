import os
import boto3
import requests
from core.utils.env_config import load_credential


def create_session():
    return boto3.Session(
        aws_access_key_id=load_credential("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=load_credential("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )


class AWSS3Client:
    """AWS S3 client for uploading and downloading files"""
    def __init__(self):
        self._session = boto3.Session(
            aws_access_key_id=load_credential("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=load_credential("AWS_SECRET_ACCESS_KEY"),
            region_name="us-east-1"
        )
        self._s3_client = self._session.client('s3')

    def get_session(self):
        return self._session

    def get_location(self):
        return self._session.client('location')

    def get_s3(self):
        return self._session.client('s3')

    def delete_s3_object(self, bucket_name, object_key):
        s3 = self.get_s3()
        # use request to check if object exists
        response = requests.head(f'https://{bucket_name}.s3.amazonaws.com/{object_key}')
        if response.status_code != 200:
            raise Exception(f'https://{bucket_name}.s3.amazonaws.com/{object_key} doesn\'t exist')
        try:
            object_key_with_space = object_key.replace('+', ' ')
            s3.delete_object(Bucket=bucket_name, Key=object_key_with_space)
            response = requests.head(f'https://{bucket_name}.s3.amazonaws.com/{object_key}')
            if response.status_code == 200:
                raise Exception(f'https://{bucket_name}.s3.amazonaws.com/{object_key} still exists')
            print(f'Successfully deleted {object_key} from {bucket_name}')
        except Exception as e:
            print(f'Error: {e}')

    def download_s3_file_by_prefix(self, bucket_name, prefix, download_path='.'):
        """
        Download the first S3 file that matches the given prefix
        
        Args:
            bucket_name (str): Name of the S3 bucket
            prefix (str): Prefix to search for
            download_path (str): Local path to download file to (default: current directory)
            
        Returns:
            str: Path of downloaded file, or None if no file found
        """
        s3 = self.get_s3()
        
        try:
            # List objects with the given prefix
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=1
            )
            
            # Check if any object was found
            if 'Contents' not in response or not response['Contents']:
                print(f'No files found with prefix {prefix}')
                return None
                
            # Get the first matching object
            file_key = response['Contents'][0]['Key']
            local_file_path = f"{download_path}/{file_key.split('/')[-1]}"
            
            # Download the file
            s3.download_file(bucket_name, file_key, local_file_path)
            print(f'Successfully downloaded {file_key} to {local_file_path}')
            
            return local_file_path
            
        except Exception as e:
            raise Exception(f'Error download_s3_file_by_prefix: {e}')
        
    def upload_s3_file(self, bucket_name: str, local_file_path: str, s3_key: str):
        """
        Upload a file to S3
        """
        try:
            self._s3_client.upload_file(
                Filename=local_file_path,
                Bucket=bucket_name,
                Key=s3_key
            )
        except Exception as e:
            raise Exception(f"Failed to upload {local_file_path}: {str(e)}") from e


class BedrockClient:
    def __init__(self):
        self._session = create_session()
        self._bedrock_agent_client = self._session.client(service_name="bedrock-agent-runtime")

    def retrieve_from_knowledge_base(self, knowledge_base_id, query, max_results=5):
        """
        Retrieve information from an AWS Bedrock Knowledge Base.
        
        Args:
            knowledge_base_id (str): The ID of the knowledge base to query
            query (str): The search query to retrieve relevant information
            max_results (int): Maximum number of results to return
            region (str): AWS region where the knowledge base is located
            
        Returns:
            retrieval_results (list): The response containing retrieved passages
            [{"content": {"text": ""}}, ...]
        """
        # Make the retrieve request
        response = self._bedrock_agent_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        retrieval_results = response['retrievalResults']
        return retrieval_results