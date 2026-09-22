from abc import ABC, abstractmethod


class HedgeExchange(ABC):

    @abstractmethod
    def get_position(self, symbol):
        pass

    @abstractmethod
    def open_short(self, symbol, amount):
        pass

    @abstractmethod
    def close_short(self, symbol, amount):
        pass