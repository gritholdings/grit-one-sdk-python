import requests
from core.utils.aws.s3 import S3Client
from core.utils.github import GithubClient
from core_agent.models import KnowledgeBase
from core_agent.store import KnowledgeBaseVectorStoreService


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
        """
        1. Recursively fetches all files (and subfolders) from a GitHub repo folder.
        2. Uploads them to S3.
        3. Removes S3 files that no longer exist in GitHub (full sync).
        
        Returns a dictionary with sync details.
        """

        # 1. Fetch the list of GitHub files (paths and download URLs)
        files_info = self.github_client.fetch_github_contents(
            owner=github_owner,
            repo=github_repo,
            path=github_folder,
            branch=github_branch
        )

        # 2. Upload each file to S3
        for file_item in files_info:
            file_url = file_item['download_url']
            file_path = file_item['path']  # Use the GitHub path as the S3 object key

            file_response = requests.get(file_url)
            if file_response.status_code == 200:
                self.s3_client.upload_file_to_s3(file_response.content, file_path)
            else:
                print(
                    f"Failed to download {file_url} "
                    f"(status code: {file_response.status_code})"
                )

        # 3. Remove files in S3 that no longer exist in GitHub
        #    We'll assume the prefix to list in S3 is the same as `github_folder`.
        s3_existing_keys = self.s3_client.list_s3_files_in_prefix(github_folder)

        # GitHub file paths
        github_file_paths = set(item['path'] for item in files_info)

        # Find which S3 keys are not in the GitHub folder
        to_delete = [key for key in s3_existing_keys if key not in github_file_paths]

        if to_delete:
            print("Removing old files from S3 that no longer exist in GitHub:")
            for key in to_delete:
                print(f"  - {key}")
            self.s3_client.delete_s3_files(to_delete)

        # Return a dictionary instead of a Django JsonResponse
        return {
            "status": "success",
            "message": "S3 folder synced with GitHub repository folder",
            "total_files_uploaded": len(files_info),
            "files_removed": len(to_delete),
        }

    def sync_data_sources_to_vector_store(self):
        # 1. Get list of knowledge bases
        knowledge_bases = KnowledgeBase.objects.all()
        for knowledge_base in knowledge_bases:
            # Get data source
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
                        # 2. For each knowledge base, fetch the list of GitHub files (paths and download URLs)
                        files_info = self.github_client.fetch_github_contents(
                            owner=owner,
                            repo=repo,
                            path=folder,
                            branch=branch
                        )

                        # 3. Upload each file to vector store
                        # If file already exists, it will just update the content
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
                        # 4. Remove files in vector store that no longer exist in GitHub
                        #    We'll assume the prefix to list in vector store is the same as `folder`.
                        existing_vectorstore_chunks = self.kb_vectorstore_service.list_documents(
                            knowledge_base_id=str(knowledge_base.id),
                            prefix=folder
                        )
                        github_file_paths = set(item['path'] for item in files_info)
                        to_delete_list = []
                        for chunk_path in existing_vectorstore_chunks:
                            # Remove the "_chunk_X" suffix to get the original file path
                            # Split by "_chunk_" and take the first part
                            base_file_path = chunk_path.split("_chunk_")[0]\
                                if "_chunk_" in chunk_path else chunk_path
                            
                            # Check if the base file path exists in github_file_paths
                            if base_file_path not in github_file_paths:
                                # If not, add this chunk to the deletion list
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