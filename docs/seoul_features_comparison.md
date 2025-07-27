# Seoul XGBoost Features Comparison

## Paper's 36 Features (12 indexes × 3 statistics each)

### Base 12 Indexes:

**Sleep Indexes (10):**
1. Sleep amplitude (coefficient of variation of wake amounts every 10 min)
2. Sleep percentage (percentage of total sleep time)
3. Long Num (number of long sleep windows >3.75h)
4. Long Len (total length of long windows)
5. Long ST (sleep time in long windows)
6. Long WT (wake time in long windows)
7. Short Num (number of short sleep windows <3.75h)
8. Short Len (total length of short windows)
9. Short ST (sleep time in short windows)
10. Short WT (wake time in short windows)

**Circadian Indexes (2):**
11. Circadian phase (DLMO - estimated from CBT minimum - 7h)
12. Circadian amplitude (amplitude of simulated CBT rhythm)

**For each index, calculate:**
- Mean (over patient's history)
- Standard deviation (over patient's history)
- Z-score (today's value relative to patient's baseline)

Total: 12 × 3 = 36 features

## Our Current Implementation Issues:

1. **We're not implementing the paper's exact features**
   - Missing: sleep amplitude, Long/Short window metrics
   - Added features not in paper: sleep fragmentation index, activity features, heart rate features

2. **Sleep window calculation is CRITICAL**
   - Merge sleep periods <1 hour apart
   - Disregard awakenings and sleep <10 min
   - Categorize as long (>3.75h) or short (<3.75h)
   - Calculate metrics for EACH category separately

3. **Z-scores need patient baselines**
   - Paper uses individual patient's historical mean/std
   - We're using population norms (incorrect!)

4. **Circadian phase calculation**
   - Paper uses mathematical model of core body temperature
   - DLMO = CBT_min - 7 hours
   - We're using a default value (incorrect!)

## Required Fixes:

1. Implement exact Seoul features from paper
2. Add sleep window merging with 3.75h threshold
3. Calculate patient-specific baselines for Z-scores
4. Implement proper circadian rhythm modeling