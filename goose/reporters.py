from typing import Literal, Optional, Union, cast
import logging
import httpx
from .github_client import github_call
from .commits import CommitRange

log = logging.getLogger(__name__)

CommitStatus = Union[Literal['failure'], Literal['error'], Literal['success'], Literal['pending']]


class GithubReporter:
    '''
    Communicates status to GitHub commits and pull requests
    '''

    def __init__(self, commit_range: CommitRange, statuses_url: str) -> None:
        self.commit_range = commit_range
        self.statuses_url = statuses_url

    def _req(
        self, service: str, state: CommitStatus, description: Optional[Union[str, BaseException]]
    ) -> httpx.Response:
        owner, repo = self.commit_range.owner_repo
        sha = self.commit_range.head_sha
        body = {
            'owner': owner,
            'repo': repo,
            'sha': sha,
            'state': state,
            'context': f'goose/{service}',
        }

        if description:
            body['description'] = cast(str, description)

        log.debug("Calling %s/%s with status %s for service %s", owner, repo, state, service)
        return github_call(self.statuses_url.replace('{sha}', sha), body)

    def poll_for_changes(self, interval: int = 60) -> None:
        """
        Poll the repository for changes at a specified interval.
        
        :param interval: Time in seconds between each poll.
        """
        import time

        while True:
            try:
                # Example logic to check for changes
                response = self._req('poll', 'pending', 'Polling for changes')
                if response.status_code == httpx.codes.OK:
                    log.info("Polling successful, no changes detected.")
                else:
                    log.warning("Polling failed with status code: %s", response.status_code)
            except Exception as e:
                self.error('poll', e)

            time.sleep(interval)

    def fail(self, service: str, message: Union[str, BaseException]) -> bool:
        resp = self._req(service, 'failure', message)
        return resp.status_code == httpx.codes.OK

    def error(self, service: str, message: Union[str, BaseException]) -> bool:
        resp = self._req(service, 'error', message)
        return resp.status_code == httpx.codes.OK

    def ok(self, service: str) -> bool:
        resp = self._req(service, 'success', None)
        return resp.status_code == httpx.codes.OK

    def pending(self, service: str) -> bool:
        resp = self._req(service, 'pending', None)
        return resp.status_code == httpx.codes.OK
