import os
from typing import List

from application.docker.services.DockerClientService import DockerClientService

from domain.models.paths import Paths
from domain.models.container_info import ContainerInfo

from domain.services.contracts.abstract_path_service import AbstractPathService
from domain.services.contracts.abstract_job_utility_service import AbstractJobUtilityService

from domain.exceptions.job_exception import ContainerNotFound, ListIndexOutOfRange

from shared.helpers.get_model_zip import get_downloadable_zip
from shared.helpers.alias_provider_sql import get_alias_from_name, get_name_from_alias


class JobUtilityService(AbstractJobUtilityService):
    def __init__(self, path_service: AbstractPathService, docker_client: DockerClientService):
        self.paths: Paths = path_service.get_paths()
        self.client: DockerClientService = docker_client.client

    def _get_running_container(self) -> List[str]:
        # get running containers by image name
        containers: List[str] = []
        try:
            for container in self.client.containers.list():
                if container.image.attrs['RepoTags'][0] == self.paths.image_name + ":latest":
                    containers.append(get_alias_from_name(container.name))
            # None values may appear when a container is not inside the DB
            return list(filter(None, containers))
        except Exception as e:
            raise ListIndexOutOfRange(additional_message="Container ID: ", container_id=container.short_id)

    def get_all_jobs(self) -> List[str]:
        return self._get_running_container()

    def get_finished_jobs(self) -> List[str]:
        downloadable_models: List[str] = []
        downloadable_jobs: List[str] = []

        if os.path.isdir(self.paths.servable_folder):
            downloadable_models = list(get_downloadable_zip(folder_path=self.paths.servable_folder).keys())
            downloadable_jobs = [model.split(".zip")[0] for model in downloadable_models]

        running_containers: List[str] = self._get_running_container()
        finished_jobs: List[str] = list(set(running_containers).intersection(set(downloadable_jobs)))
        return finished_jobs

    def get_container_logs(self, container_info: ContainerInfo) -> List[str]:
        logs: str = ""
        container_alias: str = get_name_from_alias(alias=container_info.name)

        try:
            for container in self.client.containers.list():
                if container.name == container_alias:
                    logs = container.logs()

            log_list: List[str] = logs.decode('utf-8').splitlines()
            return log_list
        except Exception:
            raise ContainerNotFound(container_name=container_info.name)
