## 🚨 Need Definitive Answers: XGBoost Model Requirements (Baselines & Labeling)

### Summary
We have conflicting interpretations of the XGBoost paper requirements and need someone to carefully read the primary literature to establish a definitive source of truth. This affects whether we should deprecate or properly integrate existing baseline and labeling features.

### Background
Our codebase has two features that may or may not be needed:

1. **Statistical Baseline System** (`BaselineRepositoryInterface`)
   - Calculates personal mean/std for features
   - Currently has bugs (zero-hour sleep corruption)
   - May be completely unused

2. **Episode Labeling System** (`big-mood label` commands)
   - Allows users to label past mood episodes
   - Sophisticated CLI interface
   - Unclear if required for predictions

### The Confusion
We've had multiple contradictory interpretations of the [XGBoost paper](../docs/literature/converted_markdown/xgboost-mood/xgboost-mood.md):

**Interpretation 1:** Models require personalized training
- Each user must label their episodes
- Need "60-day windows with 30 episode days"
- Models learn individual patterns

**Interpretation 2:** Models are population-based
- Pre-trained on 168 Korean patients
- Work immediately with just sleep data
- No labeling required

### Critical Questions Needing Definitive Answers

1. **Are the XGBoost weights population models or personalization frameworks?**
   - What exactly do the JSON files in `/model_weights/xgboost/` represent?
   - Can they make predictions immediately or need user-specific training?

2. **What does "60-day range where half represented episodic days" mean?**
   - Is this a requirement for users?
   - Or just the paper's validation methodology?

3. **Do the models need labeled episodes to function?**
   - The paper mentions "trained psychiatrist assessed... mood episode recurrence"
   - Is this for training the published weights or for each user?

4. **Are Z-scores calculated separately or part of the 36 features?**
   - The paper mentions "mean, SD, and Z-score" for each feature
   - Does this require baseline tracking or just current calculation?

5. **What's the difference between Figures 4-5 (AUC 0.925) and Figure 6 (AUC 0.80)?**
   - Different methodologies?
   - Different requirements?

### Current Code Status

**Baseline System:**
```python
# domain/repositories/baseline_repository.py
class BaselineRepositoryInterface(ABC):
    # Stores personal statistics
    # Has bugs, may be unused
```

**Labeling System:**
```python
# interfaces/cli/commands/label.py
@click.command()
def episode(...):
    # Sophisticated labeling interface
    # Unclear if needed
```

### What We Think (But Need Explicit Confirmation)

After multiple readings, we LIKELY have the correct understanding now:
- **XGBoost models are population-based** (no labeling needed)
- **Baseline calculations are unused** (can be deprecated)
- **Labeling exists for future personalization only**
- The "60-day windows" were for paper validation, not user requirements

We believe this is the source of truth based on:
- Line 88: "trained on the randomly sampled 80% of the entire dataset"
- 44,787 total days pooled from all 168 patients
- AUC 0.925/0.984/0.985 from population model

**BUT** - we've flip-flopped multiple times and need someone to explicitly confirm by carefully reading the entire paper, especially the methodology section.

### Action Needed

1. **Read the XGBoost paper carefully** (especially methodology sections)
2. **Provide definitive answers** to the 5 questions above
3. **Recommend whether to:**
   - Keep and fix baseline system
   - Keep labeling for future use
   - Deprecate both as unnecessary
   - Something else?

### Why This Matters

- We're about to have open source contributors
- Documentation is currently contradictory
- Core functionality understanding affects everything
- Need to know what to tell users

### Resources

- Paper: `/docs/literature/converted_markdown/xgboost-mood/xgboost-mood.md`
- Current interpretations: 
  - `/XGBOOST_MODELS_CORRECTED_UNDERSTANDING.md`
  - `/CRITICAL_MODEL_REQUIREMENTS_DISCOVERY.md` (outdated?)
  - `/HOW_THE_MODELS_ACTUALLY_WORK.md` (which version is right?)

### Help Wanted

This is a perfect issue for someone who:
- Enjoys reading academic papers carefully
- Can provide clear, definitive answers
- Understands the difference between training and inference
- Can help us stop flip-flopping!

### Labels
- help-wanted
- documentation
- critical
- good-first-issue
- needs-investigation