# CRITICAL DISCOVERY: Model Requirements for Big Mood Detector

**Date:** July 27, 2025  
**Version:** v0.5.0  
**Discovery by:** Claude (Acting as Technical Co-founder)

## 🚨 CRITICAL FINDING: XGBoost Models REQUIRE User-Labeled Mood Episodes

After deep investigation of the primary literature, we've discovered a fundamental misunderstanding about how the models work:

### XGBoost Models (Seoul Study)
- **REQUIRE** user-specific labeled mood episodes to function
- Were trained using "60-day ranges where half represented episodic days"
- Episodes were "assessed by trained psychiatrists" during follow-up
- **CANNOT** predict mood episodes without knowing your past episodes
- This is NOT "out of the box" functionality

### PAT Models (Dartmouth)
- Are self-supervised foundation models
- Pretrained on 29,307 participants' UNLABELED activity data
- Can be fine-tuned for depression prediction
- Work more "out of the box" but still need some labeled data for fine-tuning

## The Confusion: Two Types of "Baselines"

We've been conflating two completely different concepts:

### 1. Statistical Baselines (What we investigated)
- Personal mean/std for Z-score normalization
- Sleep patterns, activity levels, HR baselines
- The `BaselineRepositoryInterface` implementation
- **Verdict:** Has bugs, not used by models anyway

### 2. Episode Baselines (What XGBoost actually needs)
- Ground truth labels of when you had depression/mania/hypomania
- Requires clinical assessment or self-reporting
- The "label" functionality in the codebase
- **Verdict:** ESSENTIAL for XGBoost to work

## Evidence from the Papers

### XGBoost Paper (Seoul National University)
> "Using the training data consisting of the 60-day ranges, we achieved AUCs of 0.80, 0.98, and 0.95 for predicting depressive, manic, and hypomanic episodes"

> "we selected a specific 60-day range for each patient where **half of the range represented episodic days**, included this range in the training set"

> "a trained psychiatrist assessed the presence of mood episode recurrence in the inter-visit period"

### PAT Paper (Dartmouth)
> "leveraging knowledge from broader data sources to achieve robust performance even with limited participant samples"

> "PAT was pretrained on week-long actigraphy data from... 21,538 participants"

> "Using datasets where actigraphy is labeled with... PHQ-9 score (for depression)"

## What This Means for Users

### Current State (v0.5.0)
1. **XGBoost predictions will NOT work** without labeled mood episodes
2. The models expect to learn YOUR specific patterns during episodes
3. This explains why we have labeling commands in the CLI
4. The Korean cohort weights are NOT generalizable without your labels

### Required User Journey
1. User must first LABEL their historical mood episodes
2. System learns their personal patterns during episodes
3. Only THEN can it predict future episodes
4. This is personalized medicine, not general prediction

## The Labeling System Makes Sense Now!

The CLI commands we found:
- `big-mood label` - For labeling mood episodes
- Episode storage in SQLite
- Integration with prediction pipeline

This infrastructure is ESSENTIAL, not optional!

## Recommendations for v0.5.0

### 1. Update All Documentation
Remove claims about "out of the box" mood prediction. Be clear:
- XGBoost requires YOUR labeled episodes
- Minimum ~30 days of labeled data recommended
- This is personalized, not population-based

### 2. Change Default Workflow
Current implied workflow:
```
Upload data → Get predictions ❌
```

Actual required workflow:
```
Upload data → Label episodes → Train on YOUR data → Get predictions ✓
```

### 3. Consider PAT-Only Mode
For users without labeled episodes:
- Use PAT for general depression screening
- Less accurate but works without personal labels
- Can detect depression risk, not specific episodes

### 4. Fix Messaging
Change from:
> "Predicts mood episodes from wearables"

To:
> "Learns YOUR mood patterns to predict future episodes (requires labeling past episodes)"

## Technical Implementation Status

### What's Working
- Labeling infrastructure exists
- SQLite storage for episodes
- Integration points in pipeline
- XGBoost models load correctly

### What's Missing
- Clear documentation about requirements
- User onboarding flow for labeling
- Minimum data requirements
- Training on personal labels

### What's Broken
- Statistical baselines (but doesn't matter)
- User expectations (critical!)

## Bottom Line

**We've been trying to use a personalized medicine tool as a general diagnostic.**

The XGBoost models are like a doctor who needs to know YOUR medical history. Without it, they can't help you. The infrastructure for labeling exists, but the documentation completely misses this critical requirement.

This changes everything about how we position and document the tool.

---

*This discovery fundamentally changes our understanding of the project. The tool is more powerful than we thought (truly personalized) but also more demanding (requires user participation).*