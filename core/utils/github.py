import requests
import logging
from core.utils.env_config import load_credential


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GithubClient:
    def __init__(self, token: str):
        self.token = load_credential("GITHUB_TOKEN")

    def fetch_github_contents(self, owner: str, repo: str, path: str, branch: str = 'main'):
        """
        Recursively fetches all files from a GitHub repository folder (and subfolders).
        Returns a list of dicts containing 'download_url' and 'path'.
        """
        files = []
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                data = [data]

            for item in data:
                if item['type'] == 'file':
                    files.append({
                        'download_url': item['download_url'],
                        'path': item['path'],
                    })
                elif item['type'] == 'dir':
                    subfolder_files = self.fetch_github_contents(owner, repo, item['path'], branch=branch)
                    files.extend(subfolder_files)
        else:
            logger.error(f"Failed to fetch {url} (status code: {response.status_code})")

        return files