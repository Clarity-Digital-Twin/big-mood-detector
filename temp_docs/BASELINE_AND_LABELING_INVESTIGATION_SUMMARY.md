# Baseline and Labeling Investigation Summary

⚠️ **PARTIAL CORRECTION:** This investigation correctly identified baseline bugs but incorrectly concluded that labeling is required. See `/XGBOOST_MODELS_CORRECTED_UNDERSTANDING.md` for updated model understanding.

**Date:** July 27, 2025  
**Investigation by:** Claude (Acting as Technical Co-founder)

## Executive Summary

We investigated the "baseline" implementation after discovering it wasn't working as expected. This led to a MUCH bigger discovery: **the XGBoost models require user-labeled mood episodes to function**. We've been fundamentally misunderstanding how these models work.

## Investigation Journey

### 1. Started with Statistical Baselines
- Found `BaselineRepositoryInterface` and implementations
- Discovered critical bugs (zero-hour sleep corruption)
- Realized models don't use personalized Z-scores anyway
- **Verdict:** Broken but irrelevant

### 2. Read the Primary Literature
- XGBoost paper: "60-day ranges where half represented episodic days"
- PAT paper: "pretrained on 29,307 participants" (no labels needed)
- **Key insight:** Papers describe different approaches

### 3. The "Aha!" Moment
Two completely different concepts both called "baselines":
- **Statistical baselines:** Personal mean/std for normalization
- **Episode baselines:** YOUR labeled mood history (ground truth)

## Critical Findings

### XGBoost Models (Seoul)
- **Not population models** - they're personalization frameworks
- Require YOUR mood episode labels to learn YOUR patterns  
- The Korean cohort weights are just initialization
- Think: "AI that learns YOUR warning signs"

### PAT Models (Dartmouth)
- Foundation models pretrained on unlabeled data
- Can do general depression screening
- Less accurate but works "out of the box"
- Think: "Digital PHQ-9 questionnaire"

### The Labeling System
```bash
big-mood label episode --date 2024-01-15 --mood depressive --severity 4
```
This isn't optional - it's the CORE REQUIREMENT for XGBoost!

## What This Changes

### Before (Wrong Understanding)
- Upload data → Get predictions
- Models work for anyone immediately
- Baselines were about statistics

### After (Correct Understanding)  
- Upload data → Label episodes → Train on YOUR patterns → Get predictions
- Models need YOUR history to work
- "Baselines" are YOUR labeled episodes

## Implications

### For Users
- Must participate by labeling their episodes
- More work but more accurate (truly personalized)
- Can start with PAT for immediate (less accurate) results

### For Documentation
- Everything needs updating
- Current claims are incorrect
- Need clear onboarding flow

### For Development
- Labeling system is critical infrastructure
- Need personal model training pipeline
- Statistical baselines can be removed

## Technical Status

### Working
- Model loading ✓
- Labeling CLI ✓  
- Episode storage ✓
- PAT inference ✓

### Broken
- Statistical baselines (doesn't matter)
- Documentation (CRITICAL!)
- User expectations (CRITICAL!)

### Missing
- Personal model training
- Onboarding flow
- Data sufficiency checks
- Clear requirements

## Recommendations

### Immediate (v0.5.0)
1. **Fix all documentation** - Be honest about requirements
2. **Disable statistical baselines** - They're broken and unused
3. **Add prominent warnings** - "Requires labeling your episodes"
4. **Create tutorial** - Walk users through labeling

### Short Term (v0.6.0)
1. **Personal training pipeline** - Use labeled data to fine-tune
2. **Data checks** - Ensure sufficient episodes before training
3. **Progress indicators** - Show labeling progress
4. **Hybrid approach** - PAT screening → XGBoost personalization

### Long Term
1. **Transfer learning** - Can Korean patterns help initially?
2. **Community features** - Share patterns (privacy-preserving)
3. **Semi-supervised** - Reduce labeling burden
4. **Clinical validation** - Verify personalized approach

## The Bottom Line

**We built personalized medicine software but documented it as a general diagnostic tool.**

This is actually MORE impressive - true personalization! But we must be honest about what it requires from users.

## Files Created

1. **BASELINE_IMPLEMENTATION_ANALYSIS.md** - Deep dive into statistical baselines
2. **CRITICAL_MODEL_REQUIREMENTS_DISCOVERY.md** - The big discovery about labeling
3. **HOW_THE_MODELS_ACTUALLY_WORK.md** - User-facing explanation
4. **issues/baseline-implementation-critical-bugs.md** - GitHub issue for baseline bugs
5. **issues/critical-model-requirements-misunderstanding.md** - GitHub issue for the main problem

## Conclusion

The confusion about "baselines" led us to discover a fundamental misunderstanding about the entire project. The statistical baseline implementation has bugs but doesn't matter. What matters is that we've been promising general predictions when the models actually require personalized training with labeled episodes.

This changes everything about how we position, document, and develop Big Mood Detector.

---

*Investigation complete. The truth is more complex but also more powerful than we thought.*