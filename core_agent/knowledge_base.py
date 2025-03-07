import requests
from core.utils.aws.s3 import S3Client
from core.utils.github import GithubClient


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