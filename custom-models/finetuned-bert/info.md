## File Description

finetuning_bert_base_for_table_classification -> trying out base bert model with balanced dataset
table_classifier_mod_bert_trainer(2) -> initial attempt to train the modern bert model (got bad performance in true positive prediction.

## Key take aways

1. I think I should use recall as the compute metrics in place of the f1 score. The reason is that we want to make a model which predicts yes(table should be included more that no). We can have some error in the unnecesary prediction.

2. Trying to fix the imbalanced dataset with down sampling and weighted classes.
