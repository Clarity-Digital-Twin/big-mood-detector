# Questions and Concerns After Investigation

**Date:** July 27, 2025  
**Status:** Post-investigation of baseline/labeling requirements

## Critical Questions

### 1. User Acquisition & Onboarding
- **Q:** How do we attract users when they must label episodes first?
- **Q:** What if users don't remember exact episode dates?
- **Q:** How many labeled episodes are truly needed for accuracy?
- **Q:** Can we provide value before full labeling?

### 2. Model Generalization
- **Q:** Do the Korean cohort XGBoost weights transfer at all to other populations?
- **Q:** Should we even include them, or train from scratch per user?
- **Q:** What's the minimum viable training data?
- **Q:** Could we use PAT embeddings as features for XGBoost?

### 3. Clinical Validity
- **Q:** How do we handle self-labeling vs clinical assessment?
- **Q:** What about subclinical episodes users might miss?
- **Q:** How to validate user labels?
- **Q:** Should we require clinical diagnosis first?

### 4. Technical Architecture
- **Q:** Should we remove the broken statistical baseline code?
- **Q:** How to implement personal model training efficiently?
- **Q:** Where to store personalized models?
- **Q:** How to handle model updates as users add more labels?

### 5. Ethical Concerns
- **Q:** Are we giving false hope with "predictions"?
- **Q:** How to communicate uncertainty appropriately?
- **Q:** What if personalized models overfit to limited data?
- **Q:** Privacy implications of storing mood episode history?

## Key Concerns

### 1. Expectation Management
**Concern:** Current documentation sets impossible expectations
- Users expect immediate predictions
- Reality requires significant user effort
- Risk of user disappointment and abandonment

### 2. Chicken-and-Egg Problem
**Concern:** Need episodes to predict episodes
- Users most need predictions when they don't have history
- By the time they have enough labeled data, patterns may change
- How to provide value during the "learning phase"?

### 3. Data Quality
**Concern:** Self-reported labels may be unreliable
- Memory bias about past episodes
- Difficulty distinguishing episode types
- No clinical validation of labels
- Risk of garbage-in, garbage-out

### 4. Model Validity
**Concern:** Korean cohort may not generalize
- Trained on specific population (age 18-35, Korean)
- Different cultural expressions of mood
- Different lifestyle patterns
- May need complete retraining per population

### 5. Legal/Medical Device
**Concern:** Personalized predictions inch closer to medical device
- Higher regulatory scrutiny
- Liability concerns
- Need for clinical validation
- FDA/CE marking requirements?

## Philosophical Questions

### Is This The Right Approach?
- Should we pivot to population-level models?
- Is personalization worth the complexity?
- Would clinicians actually use this?
- Are we solving a real problem?

### What's Our True Value Proposition?
- Personal mood tracking assistant?
- Clinical decision support tool?
- Research platform?
- Self-monitoring system?

### Who Is Our Real User?
- Individuals with mood disorders?
- Clinicians treating patients?
- Researchers studying patterns?
- Health systems preventing readmissions?

## Proposed Experiments

### 1. Minimum Viable Labeling
- Test with just 7, 14, 30 days of labels
- Measure prediction accuracy increase
- Find the sweet spot of effort vs accuracy

### 2. Transfer Learning Study
- Test Korean weights on Western cohort
- Measure if any benefit vs random initialization
- Determine if weights help or hinder

### 3. PAT-First Approach
- Start with PAT screening
- Guide labeling based on PAT predictions
- Use labels to train personalized XGBoost
- Measure improvement trajectory

### 4. Synthetic Episodes
- Could we generate synthetic episode patterns?
- Bootstrap from limited real labels?
- Use GPT to expand sparse labels?

## Next Steps Needed

### Research
1. Literature review on personalized vs population models
2. Minimum training data requirements
3. Transfer learning in healthcare
4. Self-labeling validity studies

### Development
1. Implement personal model training
2. Create labeling assistant
3. Build onboarding flow
4. Add uncertainty quantification

### Business
1. Redefine value proposition
2. Identify target user segment
3. Regulatory pathway assessment
4. Competitive analysis with new understanding

## The Big Question

**Given what we now know, should we continue with the current approach or pivot?**

Options:
1. **Stay the course** - Fix docs, implement personal training
2. **Hybrid approach** - PAT for screening, XGBoost for personalization
3. **Pivot to PAT** - Focus on foundation model approach
4. **New direction** - Different problem/solution fit

---

*These questions need answers before v0.5.0 can truly ship with integrity.*