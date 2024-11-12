from abc import ABC, abstractmethod
from typing import Tuple


class IBatch(ABC):
    @abstractmethod
    def get_batch_params(self) -> Tuple:
        pass
