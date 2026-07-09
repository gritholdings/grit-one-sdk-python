import logging
import requests
from grit.core.utils.aws.s3 import S3Client
from grit.core.utils.github import GithubClient, GithubClientError
from .models import KnowledgeBase
from .knowledge_fs import (
    upsert_knowledge_file,
    list_knowledge_file_paths,
    delete_knowledge_file,
)
logger = logging.getLogger(__name__)


class KnowledgeBaseClient:
    def __init__(self, bucket_name=None):
        self.s3_client = S3Client(bucket_name=bucket_name)
        self.github_client = GithubClient(token=None)
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
    def sync_data_sources_to_knowledge_files(self):
        total_files_uploaded = 0
        files_removed = 0
        errors = []
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
                        try:
                            files_info = self.github_client.fetch_github_contents(
                                owner=owner,
                                repo=repo,
                                path=folder,
                                branch=branch
                            )
                        except GithubClientError as exc:
                            logger.warning(
                                "Skipping knowledge base sync for %s/%s/%s: %s",
                                owner, repo, folder, exc,
                            )
                            errors.append(f"{owner}/{repo}/{folder}: {exc}")
                            continue
                        for file_item in files_info:
                            file_url = file_item['download_url']
                            file_path = file_item['path']
                            file_response = requests.get(file_url)
                            if file_response.status_code == 200:
                                file_response_content = file_response.content
                                if isinstance(file_response_content, bytes):
                                    file_response_content = file_response_content.decode('utf-8')
                                upsert_knowledge_file(
                                    knowledge_base_id=str(knowledge_base.id),
                                    path=file_path,
                                    content=file_response_content,
                                )
                                total_files_uploaded += 1
                            else:
                                print(
                                    f"Failed to download {file_url} "
                                    f"(status code: {file_response.status_code})"
                                )
                        existing_paths = list_knowledge_file_paths(
                            knowledge_base_id=str(knowledge_base.id),
                            prefix=folder,
                        )
                        github_file_paths = set(item['path'] for item in files_info)
                        for existing_path in existing_paths:
                            if existing_path not in github_file_paths:
                                if delete_knowledge_file(
                                    knowledge_base_id=str(knowledge_base.id),
                                    path=existing_path,
                                ):
                                    files_removed += 1
                else:
                    pass
        status = "error" if errors else "success"
        message = (
            "Knowledge base files successfully synced with GitHub repository folder"
            if not errors else
            "Knowledge base sync completed with errors; affected sources were skipped"
        )
        result = {
            "status": status,
            "message": message,
            "total_files_uploaded": total_files_uploaded,
            "files_removed": files_removed,
        }
        if errors:
            result["errors"] = errors
        return result