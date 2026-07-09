import requests
import logging
from grit.core.utils.env_config import load_credential
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GithubClientError(Exception):
    pass


class GithubClient:
    def __init__(self, token: str | None = None):
        self.token = token or load_credential("GITHUB_TOKEN")
    def fetch_github_contents(self, owner: str, repo: str, path: str, branch: str = 'main'):
        files = []
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            try:
                detail = response.json().get('message', '')
            except ValueError:
                detail = ''
            logger.error(f"Failed to fetch {url} (status code: {response.status_code})")
            raise GithubClientError(
                f"GitHub API returned {response.status_code} for {url}"
                + (f": {detail}" if detail else "")
            )
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
        return files