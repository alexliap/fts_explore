import logging
import os
from functools import partial
from typing import Callable, Optional

import hydra
import lightning
import torch
from dotenv import load_dotenv
from hydra.utils import instantiate
from omegaconf import DictConfig, open_dict
from torch.utils._pytree import tree_map
from torch.utils.data import Dataset, DistributedSampler
from uni2ts.common import hydra_util
from uni2ts.data.builder.simple import SimpleDatasetBuilder, SimpleEvalDatasetBuilder
from uni2ts.data.loader import DataLoader


def make_val_yaml(
    dataset_name: str, offset: int, eval_length: int, context_length: int = 720
):
    if offset < context_length:
        context_length = offset

    val_yaml = {
        "_target_": "uni2ts.data.builder.ConcatDatasetBuilder",
        "_args_": {
            "_target_": "uni2ts.data.builder.simple.generate_eval_builders",
            "dataset": dataset_name,
            "offset": offset,
            "eval_length": eval_length,
            "prediction_lengths": [168, 336, 504, 720],
            "context_lengths": [context_length],
            "patch_sizes": [32, 64],
            "storage_path": os.getenv("CUSTOM_DATA_PATH"),
        },
    }

    return val_yaml


def calculate_batch_variables(cfg: DictConfig, offset: int):
    max_batch_size: int = 256

    # calculate correct batch_size
    while offset < max_batch_size:
        max_batch_size = int(max_batch_size / 2)

    # caclulate correct batch_size_factor
    batch_size_factor = offset / max_batch_size

    if cfg.thorough_train:
        batch_size_factor = batch_size_factor / 2

    return max_batch_size, batch_size_factor


def prepare_model(cfg: DictConfig):
    # init model
    model = instantiate(cfg.model, _convert_="all")

    # freeze everything
    model.freeze()

    # unfreeze last encoder layer
    for param in model.module.encoder.layers[-1].parameters():
        param.requires_grad = True

    for param in model.module.param_proj.parameters():
        param.requires_grad = True

    return model


class DataModule(lightning.LightningDataModule):
    def __init__(
        self,
        cfg: DictConfig,
        train_dataset: Dataset,
        val_dataset: Optional[Dataset | list[Dataset]],
    ):
        super().__init__()
        self.cfg = cfg
        self.train_dataset = train_dataset

        if val_dataset is not None:
            self.val_dataset = val_dataset
            self.val_dataloader = self._val_dataloader

    @staticmethod
    def get_dataloader(
        dataset: Dataset,
        dataloader_func: Callable[..., DataLoader],
        shuffle: bool,
        world_size: int,
        batch_size: int,
        num_batches_per_epoch: Optional[int] = None,
    ) -> DataLoader:
        sampler = (
            DistributedSampler(
                dataset,
                num_replicas=None,
                rank=None,
                shuffle=shuffle,
                seed=0,
                drop_last=False,
            )
            if world_size > 1
            else None
        )
        return dataloader_func(
            dataset=dataset,
            shuffle=shuffle if sampler is None else None,
            sampler=sampler,
            batch_size=batch_size,
            num_batches_per_epoch=num_batches_per_epoch,
        )

    def train_dataloader(self) -> DataLoader:
        return self.get_dataloader(
            self.train_dataset,
            instantiate(self.cfg.train_dataloader, _partial_=True),
            self.cfg.train_dataloader.shuffle,
            self.trainer.world_size,
            self.train_batch_size,
            num_batches_per_epoch=self.train_num_batches_per_epoch,
        )

    def _val_dataloader(self) -> DataLoader | list[DataLoader]:
        return tree_map(
            partial(
                self.get_dataloader,
                dataloader_func=instantiate(self.cfg.val_dataloader, _partial_=True),
                shuffle=self.cfg.val_dataloader.shuffle,
                world_size=self.trainer.world_size,
                batch_size=self.val_batch_size,
                num_batches_per_epoch=None,
            ),
            self.val_dataset,
        )

    @property
    def train_batch_size(self) -> int:
        return self.cfg.train_dataloader.batch_size // (
            self.trainer.world_size * self.trainer.accumulate_grad_batches
        )

    @property
    def val_batch_size(self) -> int:
        return self.cfg.val_dataloader.batch_size // (
            self.trainer.world_size * self.trainer.accumulate_grad_batches
        )

    @property
    def train_num_batches_per_epoch(self) -> int:
        return (
            self.cfg.train_dataloader.num_batches_per_epoch
            * self.trainer.accumulate_grad_batches
        )


@hydra.main(
    version_base="1.3", config_path="cli/conf/finetune/", config_name="default.yaml"
)
def main(cfg: DictConfig):
    load_dotenv()

    storage_path = os.getenv("CUSTOM_DATA_PATH")

    if cfg.tf32:
        assert cfg.trainer.precision == 32
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

    # number of weeks where we will conduct iterative training (backtesting with refit)
    num_of_weeks = cfg.num_of_weeks
    # the amount of weeks we will progress each time
    iter_step = cfg.iter_step

    # build train & validation sets
    for i in range(1, num_of_weeks + 1, iter_step):
        train_size = i * (7 * 24)

        SimpleDatasetBuilder(
            dataset=f"{cfg.train_dataset_name}_{i}", storage_path=storage_path
        ).build_dataset(
            offset=train_size, dataset_type="wide", file=cfg.dataset_path, freq="H"
        )

    SimpleEvalDatasetBuilder(
        dataset=cfg.val_dataset_name,
        offset=None,
        windows=None,
        distance=None,
        prediction_length=None,
        context_length=None,
        patch_size=None,
        storage_path=storage_path,
    ).build_dataset(file=cfg.dataset_path, dataset_type="wide", freq="H")

    # create backtesting with refit loop
    for i in range(1, num_of_weeks + 1, iter_step):
        # same with train size
        offset = i * (7 * 24)
        eval_length = (num_of_weeks - i) * (7 * 24) + 4320

        batch_size, batch_size_factor = calculate_batch_variables(cfg, offset=offset)

        with open_dict(cfg):
            if cfg.thorough_train:
                cfg.trainer.max_epochs = i
                cfg.trainer.callbacks[2]["patience"] = int(i / 2)

            # get model from previous training iteration
            if cfg.refit and i > 1:
                prev_model = os.listdir(cfg.trainer.callbacks[1]["dirpath"])[0]
                logging.info(
                    f"Loading checkpoint from {cfg.trainer.callbacks[1]['dirpath']}"
                )
                cfg.model.checkpoint_path = os.path.join(
                    cfg.trainer.callbacks[1]["dirpath"], prev_model
                )

            # change the directory where the model is saved each time based on the week we are in
            cfg.dataset = f"{cfg.train_dataset_name}_{i}"
            cfg.trainer.callbacks[1]["dirpath"] = os.path.join(
                cfg.model_dirpath, cfg.dataset
            )
            logging.info(cfg.trainer.callbacks[1]["dirpath"])
            # modify validation dataset
            cfg.val_data = make_val_yaml(
                dataset_name=cfg.val_dataset_name,
                offset=offset,
                eval_length=eval_length,
            )
            # modify train dataloader
            cfg.train_dataloader.batch_size = batch_size
            cfg.train_dataloader.batch_size_factor = batch_size_factor
            cfg.train_dataloader.num_batches_per_epoch = int(
                torch.ceil(torch.tensor(batch_size_factor)).item()
            )

        model = prepare_model(cfg)

        if cfg.compile:
            model.module.compile(mode=cfg.compile)

        # load train dataset
        train_dataset = SimpleDatasetBuilder(
            dataset=f"{cfg.train_dataset_name}_{i}",
            weight=1000,
            storage_path=storage_path,
        ).load_dataset(model.train_transform_map)

        # load validation dataset
        val_dataset = (
            tree_map(
                lambda ds: ds.load_dataset(model.val_transform_map),
                instantiate(cfg.val_data, _convert_="all"),
            )
            if "val_data" in cfg
            else None
        )

        # init Trainer
        trainer: lightning.Trainer = instantiate(cfg.trainer)

        trainer.fit(model, datamodule=DataModule(cfg, train_dataset, val_dataset))

        del model, train_dataset, val_dataset, trainer


if __name__ == "__main__":
    main()
