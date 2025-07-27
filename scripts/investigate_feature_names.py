#!/usr/bin/env python3
"""Investigate the feature name mismatch between our code and XGBoost models."""

from big_mood_detector.infrastructure.ml_models.xgboost_models import XGBoostModelLoader

# Our feature names
loader = XGBoostModelLoader()
our_names = loader.FEATURE_NAMES

# Model's expected names from error message
model_names = [
    "ST_long_MN", "ST_long_SD", "ST_long_Zscore",
    "ST_short_MN", "ST_short_SD", "ST_short_Zscore",
    "WT_long_MN", "WT_long_SD", "WT_long_Zscore",
    "WT_short_MN", "WT_short_SD", "WT_short_Zscore",
    "LongSleepWindow_length_MN", "LongSleepWindow_length_SD", "LongSleepWindow_length_Zscore",
    "LongSleepWindow_number_MN", "LongSleepWindow_number_SD", "LongSleepWindow_number_Zscore",
    "ShortSleepWindow_length_MN", "ShortSleepWindow_length_SD", "ShortSleepWindow_length_Zscore",
    "ShortSleepWindow_number_MN", "ShortSleepWindow_number_SD", "ShortSleepWindow_number_Zscore",
    "Sleep_percentage_MN", "Sleep_percentage_SD", "Sleep_percentage_Zscore",
    "Sleep_amplitude_MN", "Sleep_amplitude_SD", "Sleep_amplitude_Zscore",
    "Circadian_phase_MN", "Circadian_phase_SD", "Circadian_phase_Zscore",
    "Circadian_amplitude_MN", "Circadian_amplitude_SD", "Circadian_amplitude_Zscore",
]

print("FEATURE NAME MISMATCH ANALYSIS")
print("="*60)
print(f"Our code expects {len(our_names)} features")
print(f"Model expects {len(model_names)} features")
print()

# Create mapping
print("MAPPING REQUIRED:")
print("-"*60)

# Map our names to model names
mapping = {}
for i, (our, model) in enumerate(zip(our_names, model_names)):
    print(f"{i+1:2d}. {our:30} -> {model}")
    mapping[our] = model

print()
print("KEY DIFFERENCES:")
print("-"*60)
print("1. Our code: 'long_ST_MN' -> Model: 'ST_long_MN'")
print("2. Our code: 'long_num_MN' -> Model: 'LongSleepWindow_number_MN'")
print("3. Our code: 'Z' suffix -> Model: 'Zscore' suffix")
print("4. Different naming conventions throughout")