import boto3
from grit.core.utils.env_config import load_credential


def create_session():
    return boto3.Session(
        aws_access_key_id=load_credential("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=load_credential("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )


class S3Client:
    def __init__(self, bucket_name):
        self._s3_client = create_session().client('s3')
        self.bucket_name = bucket_name
    def upload_file_to_s3(self, file_content: bytes, file_path: str):
        bucket_name = self.bucket_name
        self._s3_client.put_object(
            Bucket=bucket_name,
            Key=file_path,
            Body=file_content
        )
    def list_s3_files_in_prefix(self, prefix: str) -> set:
        bucket = self.bucket_name
        paginator = self._s3_client.get_paginator('list_objects_v2')
        s3_keys = set()
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    s3_keys.add(obj['Key'])
        return s3_keys
    def delete_s3_files(self, file_keys: list):
        bucket_name = self.bucket_name
        delete_objs = [{'Key': key} for key in file_keys]
        if delete_objs:
            self._s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': delete_objs}
            )