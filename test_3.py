import hydra
from dotenv import load_dotenv
from omegaconf import DictConfig

from fts_explore.finetuning.stage_two import StageTwoFinetuning


@hydra.main(
    version_base="1.3",
    config_path="cli/conf/finetune/",
    config_name="stage_two_pt.yaml",
)
def main(cfg: DictConfig):
    load_dotenv()

    stage_two = StageTwoFinetuning(cfg=cfg)

    stage_two.fit()


if __name__ == "__main__":
    main()
