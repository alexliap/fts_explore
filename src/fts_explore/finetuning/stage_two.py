import os
from typing import Optional

import lightning as L
import pandas as pd
import torch
from hydra.utils import instantiate
from loguru import logger
from omegaconf import DictConfig, open_dict
from torch.utils._pytree import tree_map
from torch.utils.data import Dataset
from uni2ts.common import hydra_util
from uni2ts.data.builder.simple import SimpleDatasetBuilder, SimpleEvalDatasetBuilder

from fts_explore.data_module import DataModule

from ..batch.batch import VariableBatch


class StageTwoFinetuning:
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg

        self.model = None
        self.train_dataset = None
        self.val_dataset = None
        self.trainer = None

        self.batch = VariableBatch()

        logger.info("Starting stage 2 of the process ...")
        logger.info(self.cfg)

        self._build_datasets()

        logger.info("Built train and validations sets ...")

    def fit(self):
        if self.cfg.refit and self.cfg.thorough:
            raise RuntimeError("refit and thorough arguents can't be both True.")

        if self.cfg.tf32:
            assert self.cfg.trainer.precision == 32
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        self._edit_patience_delta()

        # iterative train loop
        for i in range(self.cfg.start, self.cfg.time_steps + 1, self.cfg.iter_step):
            train_dataset, val_dataset = self._prepare_training_vars(counter=i)

            # init Trainer
            trainer: L.Trainer = instantiate(self.cfg.trainer)

            trainer.fit(
                self.model, datamodule=DataModule(self.cfg, train_dataset, val_dataset)
            )

            del self.model, train_dataset, val_dataset, trainer

    def _build_datasets(self) -> None:
        # build train & validation sets
        for i in range(1, self.cfg.time_steps + 1, self.cfg.iter_step):
            train_size = i * self.cfg.time_step_size

            instantiate(
                self.cfg.train_dataset, dataset=f"{self.cfg.train_dataset_name}_{i}"
            ).build_dataset(
                offset=train_size,
                dataset_type="wide",
                file=self.cfg.dataset_path,
                freq=self.cfg.freq,
            )

        # build validation dataset
        instantiate(self.cfg.validation_dataset).build_dataset(
            dataset_type="wide", file=self.cfg.dataset_path, freq=self.cfg.freq
        )

    def _prepare_model(self):
        # init Model
        self.model: L.LightningModule = instantiate(self.cfg.model, _convert_="all")
        logger.info("Model Created ...")

        # freeze everything
        self.model.freeze()

        # unfreeze last encoder layer
        for param in self.model.module.encoder.layers[-1].parameters():
            param.requires_grad = True

        for param in self.model.module.param_proj.parameters():
            param.requires_grad = True

        logger.info("Freezed necessary layers ...")

    def _prepare_training_vars(self, counter: int):
        if self.cfg.thorough:
            self.cfg.trainer.max_epochs = counter
            self.cfg.trainer.callbacks[2]["patience"] = int(counter / 2)

        self._update_validation_params(counter)

        self._calculate_batch_variables(counter)

        self._change_checkpoint_path(counter)

        if self.cfg.compile:
            self.model.module.compile(mode=self.cfg.compile)

        self._prepare_model()

        # load train dataset
        train_dataset = instantiate(
            self.cfg.train_dataset, dataset=f"{self.cfg.train_dataset_name}_{counter}"
        ).load_dataset(self.model.train_transform_map)

        # load validation dataset
        val_dataset = (
            tree_map(
                lambda ds: ds.load_dataset(self.model.val_transform_map),
                instantiate(self.cfg.val_data, _convert_="all"),
            )
            if "val_data" in self.cfg
            else None
        )

        return train_dataset, val_dataset

    def _update_validation_params(self, counter: int) -> None:
        offset = counter * self.cfg.time_step_size

        with open_dict(self.cfg):
            if (
                self.cfg.max_context_length is not None
                and offset < self.cfg.max_context_length
            ):
                self.cfg.val_data._args_.context_lengths = [offset]

            self.cfg.val_data._args_.dataset = self.cfg.validation_dataset.dataset
            self.cfg.val_data._args_.offset = offset
            self.cfg.val_data._args_.eval_length = (
                self.cfg.time_steps - counter
            ) * self.cfg.time_step_size + self.cfg.eval_buffer

        logger.info(f"Offest: {offset}")
        logger.info(f"Context Lengths: {self.cfg.val_data._args_.context_lengths}")
        logger.info(f"Evaluation Length: {self.cfg.val_data._args_.eval_length}")

    def _calculate_batch_variables(self, counter: int) -> None:
        offset = counter * self.cfg.time_step_size

        batch_size, batch_size_factor, num_batches_per_epoch = (
            self.batch.get_batch_params(offset=offset, is_thorough=self.cfg.thorough)
        )

        with open_dict(self.cfg):
            # modify train dataloader
            self.cfg.train_dataloader.batch_size = batch_size
            self.cfg.train_dataloader.batch_size_factor = batch_size_factor
            self.cfg.train_dataloader.num_batches_per_epoch = int(
                torch.ceil(torch.tensor(num_batches_per_epoch)).item()
            )

        logger.info(f"Batch Size: {self.cfg.train_dataloader.batch_size}")

    def _change_checkpoint_path(self, counter: int):
        with open_dict(self.cfg):
            if self.cfg.refit and counter > 1:
                prev_model = os.listdir(self.cfg.trainer.callbacks[1]["dirpath"])[0]
                logger.info(
                    f"Loading checkpoint from {self.cfg.trainer.callbacks[1]['dirpath']}"
                )
                self.cfg.model.checkpoint_path = os.path.join(
                    self.cfg.trainer.callbacks[1]["dirpath"], prev_model
                )

            # change the directory where the model is saved each time based on the time_step we are in
            self.cfg.dataset = f"{self.cfg.train_dataset_name}_{counter}"
            self.cfg.trainer.callbacks[1]["dirpath"] = os.path.join(
                self.cfg.model_dirpath, self.cfg.dataset
            )
            logger.info(self.cfg.trainer.callbacks[1]["dirpath"])

    def _edit_patience_delta(self):
        if self.cfg.trainer.callbacks[2].monitor == "val/PackedMSELoss":
            dataset = pd.read_csv(self.cfg.dataset_path, index_col=0, parse_dates=True)
            data_mean = dataset.mean().item()
            delta = data_mean * self.cfg.delta_scale
            if delta > 1000:
                delta = 1000
            with open_dict(self.cfg):
                self.cfg.trainer.callbacks[2]["min_delta"] = delta

        logger.info(
            f"Patience min_delta equals to {self.cfg.trainer.callbacks[2]['min_delta']}"
        )
