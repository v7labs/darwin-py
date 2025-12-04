"""
Alternative approaches to fix the team_slug bug with less code changes
"""

# OPTION 1: Context Manager (Thread-safe with thread-local storage)
from contextlib import contextmanager
import threading

class Client:
    def __init__(self):
        self.default_team = "default-team"
        self._thread_local = threading.local()
    
    @contextmanager
    def use_team(self, team_slug):
        """Context manager to temporarily use a different team"""
        old_team = getattr(self._thread_local, 'active_team', None)
        self._thread_local.active_team = team_slug
        try:
            yield
        finally:
            self._thread_local.active_team = old_team
    
    def _get_headers(self, team_slug=None):
        # Check thread-local first, then parameter, then default
        effective_team = (
            team_slug or 
            getattr(self._thread_local, 'active_team', None) or 
            self.default_team
        )
        # Use effective_team for API key...


# Usage in RemoteDataset.pull():
def pull(self):
    with self.client.use_team(self.team):
        # All download operations here will use self.team
        download_all_images_from_annotations(...)
        # No need to pass team_slug!


# OPTION 2: Temporarily override default_team (Simpler but not thread-safe)
def pull(self):
    old_default = self.client.default_team
    try:
        self.client.default_team = self.team
        download_all_images_from_annotations(...)
    finally:
        self.client.default_team = old_default


# OPTION 3: Create a wrapper client
class ScopedClient:
    def __init__(self, client, team_slug):
        self._client = client
        self._team_slug = team_slug
    
    def _get_raw_from_full_url(self, url, **kwargs):
        # Always inject team_slug
        return self._client._get_raw_from_full_url(
            url, team_slug=self._team_slug, **kwargs
        )

def pull(self):
    scoped_client = ScopedClient(self.client, self.team)
    download_all_images_from_annotations(scoped_client, ...)
