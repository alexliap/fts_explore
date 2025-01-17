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

from fts_explore.data_module import DataModule


class StageOneFinetuning:
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg

        self.model = None
        self.train_dataset = None
        self.val_dataset = None
        self.trainer = None

        logger.info("Starting stage 2 of the process ...")
        logger.info(self.cfg)

        self._build_datasets()

        logger.info("Built train and validations sets ...")

        self._prepare_training_vars()

    def fit(self):
        self.trainer.fit(
            self.model,
            datamodule=DataModule(self.cfg, self.train_dataset, self.val_dataset),
            ckpt_path=self.cfg.ckpt_path,
        )

    def _build_datasets(self) -> None:
        # build train dataset
        instantiate(self.cfg.train_dataset).build_dataset(
            offset=self.cfg.offset,
            dataset_type="wide",
            file=self.cfg.dataset_path,
            freq=self.cfg.freq,
            date_offset=self.cfg.date_offset,
        )

        if self.cfg.validation_dataset.dataset != self.cfg.val_data._args_.dataset:
            raise ValueError(
                "Dataset name in validation_dataset and val_data must be the same."
            )

        # build validation dataset
        instantiate(self.cfg.validation_dataset).build_dataset(
            dataset_type="wide", file=self.cfg.dataset_path, freq=self.cfg.freq
        )

    def _prepare_training_vars(self):
        if self.cfg.tf32:
            assert self.cfg.trainer.precision == 32
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        self._prepare_model()

        if self.cfg.compile:
            self.model.module.compile(mode=self.cfg.compile)

        self._edit_patience_delta()

        # load train dataset
        self.train_dataset: Dataset = instantiate(self.cfg.train_dataset).load_dataset(
            self.model.train_transform_map
        )
        logger.info("Created train dataset ...")

        # load validation dataset
        self.val_dataset: Optional[Dataset | list[Dataset]] = (
            tree_map(
                lambda ds: ds.load_dataset(self.model.val_transform_map),
                instantiate(self.cfg.val_data, _convert_="all"),
            )
            if "val_data" in self.cfg
            else None
        )
        logger.info("Created validation dataset ...")

        # init Trainer
        self.trainer: L.Trainer = instantiate(self.cfg.trainer)
        logger.info("Trainer initialized ...")

        L.seed_everything(self.cfg.seed, workers=True)

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
