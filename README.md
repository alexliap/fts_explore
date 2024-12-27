# Thesis Stuff/Notes/TODOs

## This is a repo dedicated to my MSc Thesis

### Abstract (to be filled ...)

## Instructions

- Clone the repository using 
```
git clone https://github.com/alexliap/fts_explore.git
```
- to be filled ...

## ✅ TODO

- [x] Find univariate dataset for first tests

- [x] Finetune MOIRAI on this dataset in order to beat on train and validation

- [x] Find a univariate dataset of a subdomain of the first one and test thesis hypothesis
  - [x] Make iterative train loop
  - [x] Test 3 different configurations for finetuning:
    - [x] Use model of training iteration N-1 for training iteration N. 1 backward pass.
    - [x] At each training iteration use the Stage 1 model for finetuning. 1 backward pass.
    - [x] At each training iteration use the Stage 1 model for finetuning. Multiple backward passes.
      - [x] Without dropout
      - [x] With 10% dropout
      - [x] With 20% dropout
  - [x] For Stage 2, also perform iterative training of the pretrained model in order to test the hypothesis
      - [x] Without dropout
      - [x] With 20% dropout
  - [x] Experiment with different ways of evaluation/visualization
    - [x] Get forecasts and targets, in order to calculate whichever metric
- [x] Create pipeline where all the above steps are excecuted with the use of Hydra configuration files.
  - [x] Create pipeline for Stage 1
  - [x] Create pipeline for Stage 2
  - [x] Test pipeline end to end

- [ ] Search for other domains & subdomains to make experiments
  - [x] Daily crpto data (BTC & ETH)
    - Split train/validation data to 2022-01-01 => 1004 data points for validation for Stage 1
  - [x] Weather hourly & daily data from Open Meteo (Athens & Smunri)
    - Daily: Train 2014-2021 | Validation 2021-2024 

- [x] Add WQL as a comparison metric. WQL stands for weight quantile loss and is implemented by gluonTS
      as MeanWeightedSumQuantileLoss. It says mean beacuse it computes WeightedSumQuantileLoss for several quantiles
      and then calcualtes the mean.
