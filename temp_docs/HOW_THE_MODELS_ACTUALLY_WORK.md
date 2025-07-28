# How Big Mood Detector Models Actually Work

**Date:** July 27, 2025  
**Version:** v0.5.0  
**Critical Documentation**

⚠️ **UPDATE:** After careful re-reading of the paper, we've corrected our understanding. The models DO work "out of the box" without labeling. See `/XGBOOST_MODELS_CORRECTED_UNDERSTANDING.md` for details.

## The Fundamental Understanding (CORRECTED)

Big Mood Detector CAN predict mood episodes "out of the box" from your Apple Health data. The XGBoost models are population-based, pre-trained on 168 Korean patients.

## How Each Model Really Works

### 1. XGBoost Models (Primary Models)

**What they are:**
- Trained on Seoul National University cohort (168 Korean patients)
- Achieved high accuracy (AUC 0.80-0.98) in THAT specific population
- Use 36 statistical features from sleep/activity/circadian patterns

**What they REQUIRE:**
- Your personal mood episode history (labeled by you or a clinician)
- They learn YOUR specific patterns during episodes
- Minimum ~30-60 days of data with labeled episodes

**How they work:**
1. You provide historical data WITH labels of when you had episodes
2. Model learns YOUR sleep/activity patterns during depression/mania
3. Model can then predict when similar patterns occur in future

**Think of it as:** A personalized AI that learns YOUR unique warning signs

### 2. PAT Models (Foundation Models)

**What they are:**
- Pretrained on 29,307 people's activity data (no labels needed)
- Self-supervised transformer model from Dartmouth
- Can detect general depression risk (not specific episodes)

**What they REQUIRE:**
- Just activity data (no personal labels needed for basic use)
- Optional: Can be fine-tuned with your labeled data for better accuracy

**How they work:**
1. Pretrained model has learned general activity patterns
2. Can estimate depression risk based on activity alone
3. Less accurate than personalized XGBoost but works "out of the box"

**Think of it as:** A general screening tool, like a questionnaire

## The Critical Difference

### Population Model (What we thought we had)
```
Any person's data → Model → Prediction
```

### Personalized Model (What we actually have)
```
YOUR data + YOUR episode labels → Model learns YOUR patterns → Personalized predictions
```

## Required User Journey

### Current Documentation Implies:
1. Export Apple Health data
2. Run prediction
3. Get results ❌

### Actual Required Process:
1. Export Apple Health data
2. **Label your historical mood episodes**
3. System learns YOUR patterns
4. NOW it can predict future episodes ✓

## The Labeling System

The CLI includes sophisticated labeling commands:

```bash
# Label a single day
big-mood label episode --date 2024-01-15 --mood depressive --severity 4

# Label a range
big-mood label episode --date-range 2024-01-10:2024-01-20 --mood manic

# Interactive labeling with assistance
big-mood label episode --predictions predictions.csv --interactive
```

This isn't an optional feature - **it's the core requirement for XGBoost to work**.

## Evidence from the Literature

### XGBoost Paper Quote:
> "We selected a specific 60-day range for each patient where **half of the range represented episodic days**"

Translation: The model was trained on data where they KNEW which days were episodes.

### How Seoul Researchers Did It:
1. Psychiatrists assessed patients every 12 weeks
2. Documented when mood episodes occurred
3. Trained models on periods containing labeled episodes
4. Models learned each patient's unique patterns

## What This Means for Different Use Cases

### Use Case 1: "I want to know my current risk"
- Use PAT model for general screening
- Works without personal history
- Less accurate but immediate

### Use Case 2: "I want personalized predictions"
- Must label your historical episodes first
- More accurate but requires your participation
- True personalized medicine approach

### Use Case 3: "I have no episode history"
- Models cannot predict what they haven't seen
- Consider using for monitoring once you have data
- Start labeling episodes as they occur

## Why This Architecture Makes Sense

1. **Clinical Validity**: Mood patterns are highly individual
2. **Ethical Considerations**: Avoids false universality
3. **Accuracy**: Personalized models are more accurate
4. **Privacy**: Your patterns stay yours

## The Statistical Baseline Confusion

We confused two concepts:

1. **Statistical baselines** (mean/std for normalization) - Implementation has bugs but doesn't matter
2. **Episode baselines** (your labeled history) - ESSENTIAL for the system to work

## Technical Implementation Reality

### What Exists:
- ✅ Sophisticated labeling system
- ✅ Episode storage (SQLite)
- ✅ Model training infrastructure
- ✅ XGBoost/PAT model loading

### What's Missing:
- ❌ Clear documentation about requirements
- ❌ Onboarding flow for new users
- ❌ Minimum data requirements specified
- ❌ Personal model training pipeline

### What's Broken:
- 🐛 Statistical baseline calculation (but irrelevant)
- 🐛 User expectations (critical!)

## Recommendations Going Forward

### 1. Immediate (v0.5.0)
- Update ALL documentation to reflect reality
- Add prominent labeling requirements
- Create onboarding tutorial
- Set realistic expectations

### 2. Short Term (v0.6.0)
- Implement personal model training
- Add data sufficiency checks
- Create labeling assistant UI
- Add progress indicators

### 3. Long Term
- Investigate transfer learning from Korean cohort
- Build user community for shared learnings
- Research population-level patterns
- Develop hybrid approaches

## The Bottom Line

**Big Mood Detector is personalized medicine software, not a general diagnostic tool.**

It's like having a personal AI psychiatrist who needs to learn YOUR patterns first. The Korean weights are just a starting point - the real power comes from learning YOUR unique signatures.

This is actually MORE powerful than we thought, but requires user participation.

---

*This document represents our current understanding based on careful analysis of the source papers and codebase.*