#!/usr/bin/env python3
"""
Fix the Train/Test Split Bug
============================

This script recreates the NHANES data cache with a PROPER train/val/test split
matching the paper's methodology.

Paper split:
- Total with actigraphy + PHQ-9: 4,800
- Test: 2,000 (41.7%)
- Train/Val: 2,800 (58.3%)
  - Train: 2,240 (80% of 2,800)
  - Val: 560 (20% of 2,800)

Our target (with 4,103 total):
- Test: 1,710 (41.7%, matching paper proportion)
- Train/Val: 2,393 (58.3%)
  - Train: 1,914 (80%)
  - Val: 479 (20%)
"""

import logging
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Fix the train/test split in NHANES data."""
    # Load the current (incorrect) cache
    cache_path = Path("data/cache/nhanes_pat_data_subsetNone.npz")
    if not cache_path.exists():
        logger.error(f"Cache file not found: {cache_path}")
        return 1
    
    logger.info(f"Loading current cache from {cache_path}")
    data = np.load(cache_path)
    
    # Current split (all data in train/val)
    X_train_old = data['X_train']
    X_val_old = data['X_val']
    y_train_old = data['y_train']
    y_val_old = data['y_val']
    
    # Combine all data back together
    X_all = np.vstack([X_train_old, X_val_old])
    y_all = np.hstack([y_train_old, y_val_old])
    
    total_samples = len(X_all)
    logger.info(f"Total samples: {total_samples}")
    logger.info(f"Current split - Train: {len(X_train_old)}, Val: {len(X_val_old)}")
    logger.info(f"Depression prevalence: {y_all.mean():.2%} ({y_all.sum()}/{len(y_all)})")
    
    # Calculate proper split sizes to match paper proportions
    test_fraction = 0.417  # 41.7% for test (matching paper's 2000/4800)
    val_fraction = 0.2     # 20% of remaining for validation
    
    # First split: separate test set
    logger.info("\nCreating proper train/val/test split...")
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X_all, y_all,
        test_size=test_fraction,
        random_state=42,
        stratify=y_all
    )
    
    # Second split: train/val from remaining
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=val_fraction,
        random_state=42,
        stratify=y_trainval
    )
    
    # Log the new split
    logger.info(f"\nNew split sizes:")
    logger.info(f"  Train: {len(X_train)} ({len(X_train)/total_samples:.1%})")
    logger.info(f"  Val: {len(X_val)} ({len(X_val)/total_samples:.1%})")
    logger.info(f"  Test: {len(X_test)} ({len(X_test)/total_samples:.1%})")
    logger.info(f"  Total: {len(X_train) + len(X_val) + len(X_test)}")
    
    # Verify stratification
    logger.info(f"\nDepression prevalence by split:")
    logger.info(f"  Train: {y_train.mean():.2%} ({y_train.sum()}/{len(y_train)})")
    logger.info(f"  Val: {y_val.mean():.2%} ({y_val.sum()}/{len(y_val)})")
    logger.info(f"  Test: {y_test.mean():.2%} ({y_test.sum()}/{len(y_test)})")
    
    # Save the CORRECTED data with test set
    output_path = Path("data/cache/nhanes_pat_data_with_test.npz")
    logger.info(f"\nSaving corrected data to {output_path}")
    
    np.savez_compressed(
        output_path,
        X_train=X_train.astype(np.float32),
        X_val=X_val.astype(np.float32),
        X_test=X_test.astype(np.float32),
        y_train=y_train,
        y_val=y_val,
        y_test=y_test,
        # Include metadata
        split_info={
            'total_samples': total_samples,
            'train_size': len(X_train),
            'val_size': len(X_val),
            'test_size': len(X_test),
            'test_fraction': test_fraction,
            'val_fraction': val_fraction,
            'random_state': 42
        }
    )
    
    # Verify the save
    logger.info("\nVerifying saved file...")
    verify_data = np.load(output_path)
    logger.info(f"Keys in saved file: {list(verify_data.keys())}")
    logger.info(f"Has test set: {'X_test' in verify_data}")
    
    # Create a backup of the old cache
    backup_path = cache_path.with_suffix('.npz.backup_no_test')
    if not backup_path.exists():
        logger.info(f"\nBacking up old cache to {backup_path}")
        import shutil
        shutil.copy2(cache_path, backup_path)
    
    logger.info("\n" + "="*60)
    logger.info("SUCCESS! Proper train/val/test split created.")
    logger.info("Next steps:")
    logger.info("1. Update all training scripts to use 'nhanes_pat_data_with_test.npz'")
    logger.info("2. Retrain all models with the correct split")
    logger.info("3. Evaluate ONLY on the test set")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())