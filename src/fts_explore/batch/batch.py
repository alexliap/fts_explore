from .base import IBatch


class VariableBatch(IBatch):
    def __init__(self):
        self.MAX_BATCH_SIZE: int = 256

    def get_batch_params(
        self,
        offset: int,
        is_thorough: bool,
    ) -> tuple:
        return self._compute_params(offset=offset, is_thorough=is_thorough)

    def _compute_params(self, offset: int, is_thorough: bool) -> tuple:
        batch_size: int = self.MAX_BATCH_SIZE

        # calculate suitable batch_size
        while offset < self.MAX_BATCH_SIZE:
            batch_size = int(batch_size / 2)

        # caclulate correct batch_size_factor
        batch_size_factor = offset / batch_size

        num_batches_per_epoch = batch_size_factor

        if is_thorough:
            num_batches_per_epoch = num_batches_per_epoch / 2

        return batch_size, batch_size_factor, num_batches_per_epoch
