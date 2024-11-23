import hydra
from omegaconf import DictConfig

from fts_explore.finetuning.stage_one import StageOneFinetuning
from fts_explore.finetuning.stage_two import StageTwoFinetuning

# @hydra.main(
#     version_base="1.3", config_path="cli/conf/finetune/", config_name="stage_one.yaml"
# )
# def main(cfg: DictConfig):
#     stage_one = StageOneFinetuning(cfg=cfg)

#     stage_one.fit()


@hydra.main(
    version_base="1.3", config_path="cli/conf/finetune/", config_name="stage_two.yaml"
)
def main(cfg: DictConfig):
    stage_two = StageTwoFinetuning(cfg=cfg)

    stage_two.fit()


if __name__ == "__main__":
    main()
