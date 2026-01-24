import logging
from collections.abc import Mapping

import requests
from dify_plugin import ModelProvider
from dify_plugin.entities.model import ModelType
from dify_plugin.errors.model import CredentialsValidateFailedError

logger = logging.getLogger(__name__)


class CanopywaveModelProvider(ModelProvider):
    def validate_provider_credentials(self, credentials: Mapping) -> None:
        """
        Validate provider credentials
        if validate failed, raise exception

        :param credentials: provider credentials
        """
        try:
            model_instance = self.get_model_instance(ModelType.LLM)
            
            # Use a representative model for validation
            # This delegates the actual API call to the LLM class's _invoke or validate_credentials logic
            model_instance.validate_credentials(
                model="deepseek/deepseek-chat-v3.1", 
                credentials=credentials
            )
        except CredentialsValidateFailedError as ex:
            raise ex
        except Exception as ex:
            logger.exception(f"{self.get_provider_schema().provider} credentials validate failed")
            raise ex
