import requests
from grit.core.utils.aws.s3 import S3Client
from grit.core.utils.github import GithubClient
from .models import KnowledgeBase
from .store import KnowledgeBaseVectorStoreService


class KnowledgeBaseClient:
    def __init__(self, bucket_name=None):
        self.s3_client = S3Client(bucket_name=bucket_name)
        self.github_client = GithubClient(token=None)
        self.kb_vectorstore_service = KnowledgeBaseVectorStoreService()
    def upload_github_folder_to_s3(
        self,
        github_owner: str,
        github_repo: str,
        github_folder: str,
        github_branch: str = "main"
    ) -> dict:
        files_info = self.github_client.fetch_github_contents(
            owner=github_owner,
            repo=github_repo,
            path=github_folder,
            branch=github_branch
        )
        for file_item in files_info:
            file_url = file_item['download_url']
            file_path = file_item['path']
            file_response = requests.get(file_url)
            if file_response.status_code == 200:
                self.s3_client.upload_file_to_s3(file_response.content, file_path)
            else:
                print(
                    f"Failed to download {file_url} "
                    f"(status code: {file_response.status_code})"
                )
        s3_existing_keys = self.s3_client.list_s3_files_in_prefix(github_folder)
        github_file_paths = set(item['path'] for item in files_info)
        to_delete = [key for key in s3_existing_keys if key not in github_file_paths]
        if to_delete:
            print("Removing old files from S3 that no longer exist in GitHub:")
            for key in to_delete:
                print(f"  - {key}")
            self.s3_client.delete_s3_files(to_delete)
        return {
            "status": "success",
            "message": "S3 folder synced with GitHub repository folder",
            "total_files_uploaded": len(files_info),
            "files_removed": len(to_delete),
        }
    def sync_data_sources_to_vector_store(self):
        knowledge_bases = KnowledgeBase.objects.all()
        for knowledge_base in knowledge_bases:
            data_sources = knowledge_base.datasource_set.all().values()
            for data_source in data_sources:
                data_source_config = data_source['data_source_config']
                if data_source_config['type'] == 'GITHUB':
                    github_config = data_source_config.get('github_config', {})
                    source_config = github_config.get('source_config', {})
                    owner = source_config.get('owner')
                    repo = source_config.get('repo')
                    branch = source_config.get('branch')
                    inclusion_prefixes = github_config['crawler_config']['inclusion_prefixes']
                    for inclusion_prefix in inclusion_prefixes:
                        folder = inclusion_prefix
                        files_info = self.github_client.fetch_github_contents(
                            owner=owner,
                            repo=repo,
                            path=folder,
                            branch=branch
                        )
                        for file_item in files_info:
                            file_url = file_item['download_url']
                            file_path = file_item['path']
                            file_response = requests.get(file_url)
                            if file_response.status_code == 200:
                                file_response_content = file_response.content
                                if isinstance(file_response_content, bytes):
                                    file_response_content = file_response_content.decode('utf-8')
                                self.kb_vectorstore_service.add_document(
                                    knowledge_base_id=str(knowledge_base.id),
                                    file_path=file_path,
                                    text=file_response_content,
                                    metadata={}
                                )
                            else:
                                print(
                                    f"Failed to download {file_url} "
                                    f"(status code: {file_response.status_code})"
                                )
                        existing_vectorstore_chunks = self.kb_vectorstore_service.list_documents(
                            knowledge_base_id=str(knowledge_base.id),
                            prefix=folder
                        )
                        github_file_paths = set(item['path'] for item in files_info)
                        to_delete_list = []
                        for chunk_path in existing_vectorstore_chunks:
                            if "_chunk_" in chunk_path:
                                base_file_path = chunk_path.split("_chunk_")[0]
                            else:
                                base_file_path = chunk_path
                            if base_file_path not in github_file_paths:
                                to_delete_list.append(chunk_path)
                        for to_delete in to_delete_list:
                            self.kb_vectorstore_service.delete_document(
                                knowledge_base_id=str(knowledge_base.id),
                                file_path=to_delete
                            )
                else:
                    pass
        return {
            "status": "success",
            "message": ("Knowledge base vector store successfully "
                "synced with GitHub repository folder"),
            "total_files_uploaded": len(files_info),
            "files_removed": len(to_delete_list),
        }