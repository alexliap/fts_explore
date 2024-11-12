import logging
from pathlib import Path
from typing import Optional

import lightning as L
import torch
from hydra import compose, initialize
from hydra.utils import instantiate
from torch.utils._pytree import tree_map
from torch.utils.data import Dataset
from uni2ts.common import hydra_util

from fts_explore.data_module import DataModule


class StageOneFinetuning:
    def __init__(self, cfg_path: str, cfg_name: str, storage_path: str):
        logging.info(
            f"Loading configuration file at {cfg_path} with name {cfg_name} ..."
        )

        with initialize(version_base="1.3", config_path=cfg_path):
            # Load and compose the configuration
            self.cfg = compose(config_name=cfg_name)

        logging.info(
            f"Configuration file at {cfg_path} with name {cfg_name} successfully loaded ..."
        )

        self.storage_path = Path(storage_path)

        self.cfg_path = cfg_path
        self.cfg_name = cfg_name

        self.model = None
        self.train_dataset = None
        self.val_dataset = None
        self.trainer = None

        self._build_datasets()

        logging.info("Built train and validations sets ...")

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
            freq="H",
        )

        # build validation dataset
        instantiate(self.cfg.validation_dataset).build_dataset(
            dataset_type="wide", file=self.cfg.dataset_path, freq="H"
        )

    def _prepare_training_vars(self):
        if self.cfg.tf32:
            assert self.cfg.trainer.precision == 32
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        # init Model
        self.model: L.LightningModule = instantiate(self.cfg.model, _convert_="all")
        logging.info("Model Created ...")

        # freeze everything
        self.model.freeze()

        # unfreeze last encoder layer
        for param in self.model.module.encoder.layers[-1].parameters():
            param.requires_grad = True

        for param in self.model.module.param_proj.parameters():
            param.requires_grad = True

        logging.info("Freezed necessary layers ...")

        if self.cfg.compile:
            self.model.module.compile(mode=self.cfg.compile)

        # load train dataset
        self.train_dataset: Dataset = instantiate(self.cfg.train_dataset).load_dataset(
            self.model.train_transform_map
        )
        logging.info("Created train dataset ...")

        # load validation dataset
        self.val_dataset: Optional[Dataset | list[Dataset]] = (
            tree_map(
                lambda ds: ds.load_dataset(self.model.val_transform_map),
                instantiate(self.cfg.val_data, _convert_="all"),
            )
            if "val_data" in self.cfg
            else None
        )
        logging.info("Created validation dataset ...")

        # init Trainer
        self.trainer: L.Trainer = instantiate(self.cfg.trainer)
        logging.info("Trainer initialized ...")

        L.seed_everything(self.cfg.seed + self.trainer.logger.version, workers=True)
