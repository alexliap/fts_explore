from typing import Callable, Tuple, Union

from .base import IBatch


class Batch(IBatch):
    def __init__(
        self,
        type: str = "stable",
        equation: Union[None, Callable] = None,
        batch_size: Union[None, int] = None,
        batch_size_factor: Union[None, int] = None,
    ):
        self._do_checks(type, equation, batch_size, batch_size_factor)

        self.type = type
        self.equation = equation
        self.batch_size = batch_size
        self.batch_size_factor = batch_size_factor

    def get_batch_params(self) -> Tuple:
        self._compute_params()
        return self.batch_size, self.batch_size_factor

    def _compute_params(self, *args: list) -> None:
        if type == "variable":
            self.batch_size, self.batch_size_factor = self.equation(*args)

    @staticmethod
    def _do_checks(
        type: str = "stable",
        equation: Union[None, Callable] = None,
        batch_size: Union[None, int] = None,
        batch_size_factor: Union[None, int] = None,
    ) -> None:
        if type not in ["stable", "variable"]:
            raise ValueError("The type argument must either be 'stable' or 'variable'.")

        if type == "stable" and (batch_size is None or batch_size_factor is None):
            raise ValueError(
                "If type of Batch is stable batch_size and batch_size_factor must be integers."
            )

        if type == "stable" and equation is not None:
            raise ValueError(
                "In order for the equation to be used type must be 'variable'."
            )

        if type == "variable" and equation is None:
            raise ValueError("If type is 'variable' then equation can't be None.")
