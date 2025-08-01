
I’m reaching out because I’ve carefully re-implemented PAT-Conv-L on NHANES 2013-2014, following your published protocol and supplement, but can’t fully replicate your reported AUC (0.625). My best result is 0.593, with all other steps seemingly aligned.



Summary Table:


Your Paper

My Replication

Dataset

NHANES 2013-14

Same (PHQ-9, 7d)

Final n

~2,800

3,077

Model

PAT-Conv-L

PAT-Conv-L

Best Val. AUC

0.625

0.593

Pretrained

Yes

Yes (PAT-L_29k)

Data Augment

?

None



Key pipeline:
Log(x+1) transform, StandardScaler (fit on train only), PyTorch reimplementation (Conv1D patch, kernel/stride=9, embed_dim=96).

AdamW, LR=1e-4, CosineAnnealingLR, pos_weight for class imbalance, no augmentation.

Checked normalization, layer alignment, and weight loading. Peak AUC at epoch 2, then plateau.

My main questions:

Sample selection: Did you use any additional filters for NHANES beyond PHQ-9 and med exclusions? (Minimum wear time? Missing data rules?)

Augmentation or regularization: Was any augmentation or regularization used in training?

Conv1D embedding specifics: Any dropout, nonlinearity, or multi-layer embedding? I used a single Conv1D, padding=0.

Training protocol: Did you average over seeds or splits? Any warmup or early stopping?

I’ve attached my training script, logs, and model code for transparency. Even at 0.59 AUC, PAT is already valuable for clinical translation—would appreciate any insight into this last gap so I can cite and build further.


---------



RESPONSE:


Thank you so much for your interest in our model, and your clarity digital twin project looks very promising! Apologies for not getting back to your previous email earlier, as I have been on vacation this summer.


For the most part, our pipelines look similar--though can I try to make a few comments that may contribute to the small fluctuations in performance. 


For NHANES data, we actually used the PAT models trained with (21k participants) instead of (29k participants )


You can find the links for those models under “Pretrained on 2003-2004, 2005-2006, 2011-2012 NHANES Actigraphy (N=21,538)” in the github. 


This dataset excludes participants from 2013-2014 NHANES so that there wouldn’t be data leakage during the finetuning/evaluation period. 


Sample selection: As for the depression data, we had 4,800 total, and reserved 2000 for the test set, leaving us with 2,800 in the training set.


I assume you did similarly. The big dataset we used was the original 7,769 participants who provided actigraphy and medication data, and all datasets we used were subsets of that. As such, we may have lost a few participants in the process--although, we thought 4,800 was more than sufficient for a test set. Your data processing looks good though, and something that PAT is ready to train on.


Augmentation: We did not use a Log(x+1) transform, though you are on the money for using StandardScaler!


Conv1D: It’s a little different, but the PAT-Conv models should come with the conv layer internally defined already. Perhaps, it’s because you are reimplenting via Pytorch instead of Keras? I have the below definition for reference: 


        layers.Conv1D(

            filters=embed_dim, # embed_dim = 96

            kernel_size=3,

            padding='same',

            activation='relu'

        )


Training: We did use early stopping, where we saved the best weight. Also, our early stopping patience was high (250 epochs). If your peak epoch is 2 it could be worth lowering your learning rate?


Performance is similar! In Table 2 of our paper, it looks like our best performance for the depression task was actually only an AUC of 0.610 for PAT Conv-L and 0.589 for Conv-L. 


This means that your performance is not far off, and that your implementation likely works well! With a performance of 0.593, I would say that you’re definitely in the ballpark for expected performance on this task. 

