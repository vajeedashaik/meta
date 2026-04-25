from abc import ABC, abstractmethod


class BaseReward(ABC):
    @abstractmethod
    def score(self, *args, **kwargs):
        pass
