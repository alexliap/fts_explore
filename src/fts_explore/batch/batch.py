from .base import IBatch


class Batch(IBatch):
    def __init__(
        self,
        type: str = "stable",
        # equation: Union[None, Callable] = None,
        # batch_size: Union[None, int] = None,
        # batch_size_factor: Union[None, int] = None,
    ):
        if type not in ["stable", "variable"]:
            raise ValueError("The type argument must either be 'stable' or 'variable'.")

        self.type = type
        # self.equation = equation
        # self.batch_size = batch_size
        # self.batch_size_factor = batch_size_factor

    def get_batch_params(
        self,
        batch_size: int | None = None,
        batch_size_factor: int | None = None,
        num_batches_per_epoch: int | None = None,
    ) -> tuple:
        self._do_checks(
            batch_size=batch_size,
            batch_size_factor=batch_size_factor,
            num_batches_per_epoch=num_batches_per_epoch,
        )

        if self.type == "stable":
            return batch_size, batch_size_factor, num_batches_per_epoch
        elif self.type == "variable":
            return self._compute_params()

    def _compute_params(self) -> tuple:
        return 1, 2, 3

    def _do_checks(
        self,
        batch_size: int | None = None,
        batch_size_factor: int | None = None,
        num_batches_per_epoch: int | None = None,
    ) -> None:
        pass
        # if type == "stable" and (batch_size is None or batch_size_factor is None):
        #     raise ValueError(
        #         "If type of Batch is stable batch_size and batch_size_factor must be integers."
        #     )

        # if type == "stable" and equation is not None:
        #     raise ValueError(
        #         "In order for the equation to be used type must be 'variable'."
        #     )

        # if type == "variable" and equation is None:
        #     raise ValueError("If type is 'variable' then equation can't be None.")
