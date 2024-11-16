import hydra
from omegaconf import DictConfig

from fts_explore.finetuning.stage_one import StageOneFinetuning


@hydra.main(
    version_base="1.3", config_path="cli/conf/finetune/", config_name="stage_one.yaml"
)
def main(cfg: DictConfig):
    stage_one = StageOneFinetuning(cfg=cfg)

    stage_one.fit()


if __name__ == "__main__":
    main()
