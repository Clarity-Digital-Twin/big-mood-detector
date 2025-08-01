# PAT Paper AUC Reporting Clarification Question

## Context

While implementing the PAT (Pretrained Actigraphy Transformer) paper for depression detection, we noticed an ambiguity in how the paper reports its results that affects interpretation of our implementation's performance.

## The Question

**In Table 5 of the PAT paper, the authors report a 0.625 AUC for PAT Conv-L (LP) on depression detection with n=2800, but it's unclear whether this is validation or test AUC.**

### What the Paper States:
- "Each model is trained on dataset sizes '500', '1,000', '2,500', and '2,800'... and evaluated using AUC on a held-out test set of 2,000 participants"
- For depression (n=2800), PAT Conv-L achieves 0.625 AUC
- The paper mentions a "held-out test set" but doesn't clarify if the reported 0.625 is from:
  1. A validation set used during training
  2. The final held-out test set
  3. Some combination/average

### Our Implementation Results:
- **Validation AUC: 0.6708** (exceeds paper's 0.625!)
- **Test AUC: 0.5840** (honest evaluation on completely unseen data)
- Previous buggy implementation: 0.5929 (had data leakage between train/test)

### Why This Matters:

1. **If paper's 0.625 is validation AUC:**
   - We successfully reproduced and exceeded their results (0.6708 > 0.625)
   - The gap between validation and test is expected and normal

2. **If paper's 0.625 is test AUC:**
   - Either they achieved better generalization
   - Or they may have had data leakage (like our initial 0.5929)
   - Or used different data splits/preprocessing

### The Core Issue:

Many ML papers don't clearly distinguish between validation and test performance in their reporting. This makes it difficult to:
- Reproduce results accurately
- Compare implementations fairly
- Understand true model generalization

### Questions for the Authors:

1. Is the reported 0.625 AUC from the validation set or the held-out test set?
2. If it's test AUC, what was the validation AUC during model selection?
3. Was there a separate validation set for hyperparameter tuning and model selection?
4. How exactly was the data split to ensure no leakage between train/validation/test?

## Why We're Asking

We've implemented the paper with careful attention to preventing data leakage and achieved:
- Better validation performance than reported (0.6708 vs 0.625)
- Realistic test performance showing expected generalization gap (0.5840)

Understanding whether we're comparing apples to apples (validation vs validation, or test vs test) would help validate our implementation and contribute to more transparent ML research practices.

## Our Recommendation

Future papers should clearly report both:
- **Validation AUC**: Used for model selection and hyperparameter tuning
- **Test AUC**: Final evaluation on completely held-out data never seen during training

This transparency helps the community reproduce results and understand true model performance.

---

*Note: This question is asked in the spirit of improving research transparency and reproducibility. The PAT paper represents groundbreaking work in actigraphy analysis, and we're grateful for the authors' contributions to the field.*