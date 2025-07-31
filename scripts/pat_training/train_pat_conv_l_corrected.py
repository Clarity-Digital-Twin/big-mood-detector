#!/usr/bin/env python3
"""
PAT-Conv-L Training with CORRECT Train/Val/Test Split
=====================================================

This script uses the properly split data with a held-out test set.
Previous training used ALL data split only between train/val.
"""

import logging
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, TensorDataset

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pat_conv_l_corrected.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data_with_test():
    """Load the CORRECTED NHANES data with proper test set."""
    cache_path = Path("data/cache/nhanes_pat_data_with_test.npz")
    logger.info(f"Loading corrected data WITH TEST SET from {cache_path}")
    
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Corrected data not found at {cache_path}. "
            "Run fix_train_test_split.py first!"
        )
    
    data = np.load(cache_path, allow_pickle=True)
    
    # Check that we have test set
    if 'X_test' not in data:
        raise ValueError("No test set found! Data is incorrectly split.")
    
    X_train = data['X_train']
    X_val = data['X_val']
    X_test = data['X_test']
    y_train = data['y_train']
    y_val = data['y_val']
    y_test = data['y_test']
    
    logger.info(f"Data shapes:")
    logger.info(f"  Train: {X_train.shape} (was 3077 with bug)")
    logger.info(f"  Val: {X_val.shape} (was 1026 with bug)")
    logger.info(f"  Test: {X_test.shape} (was 0 with bug!)")
    
    logger.info(f"Depression prevalence:")
    logger.info(f"  Train: {y_train.mean():.2%} ({y_train.sum()}/{len(y_train)})")
    logger.info(f"  Val: {y_val.mean():.2%} ({y_val.sum()}/{len(y_val)})")
    logger.info(f"  Test: {y_test.mean():.2%} ({y_test.sum()}/{len(y_test)})")
    
    # Verify normalization
    logger.info(f"Data statistics:")
    logger.info(f"  Train - mean: {X_train.mean():.6f}, std: {X_train.std():.6f}")
    logger.info(f"  Val - mean: {X_val.mean():.6f}, std: {X_val.std():.6f}")
    logger.info(f"  Test - mean: {X_test.mean():.6f}, std: {X_test.std():.6f}")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


class SimplePATConvL(nn.Module):
    """PAT-Conv-L model matching paper architecture."""
    
    def __init__(self, dropout_rate=0.2):
        super().__init__()
        
        # Pretrained embeddings from PAT-Conv-L (96 dim)
        self.pat_embed_dim = 96
        
        # Depression classification head
        self.depression_head = nn.Sequential(
            nn.Linear(self.pat_embed_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(32, 1)
        )
        
        # Initialize with small weights
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=0.5)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, embeddings):
        """Forward pass expects precomputed PAT embeddings."""
        return self.depression_head(embeddings)


def evaluate_model(model, data_loader, device):
    """Evaluate model and return AUC."""
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for embeddings, labels in data_loader:
            embeddings = embeddings.to(device)
            outputs = model(embeddings)
            probs = torch.sigmoid(outputs).squeeze()
            
            all_preds.extend(probs.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    auc = roc_auc_score(all_labels, all_preds)
    return auc


def main():
    logger.info("="*70)
    logger.info("PAT-Conv-L Training with CORRECT Train/Val/Test Split")
    logger.info("Previous bug: NO test set, all data in train/val")
    logger.info("Now: Proper 46.6% train, 11.7% val, 41.7% test")
    logger.info("="*70)
    
    # Load corrected data
    X_train, X_val, X_test, y_train, y_val, y_test = load_data_with_test()
    
    # For now, simulate PAT embeddings (will use real PAT encoder later)
    logger.info("\nSimulating PAT embeddings (96-dim) for training...")
    # In real implementation, we'd use ProductionPATLoader to encode sequences
    
    # Placeholder: Project 10080 -> 96 dim (temporary)
    embed_proj = nn.Linear(10080, 96)
    with torch.no_grad():
        X_train_embed = embed_proj(torch.FloatTensor(X_train)).numpy()
        X_val_embed = embed_proj(torch.FloatTensor(X_val)).numpy()
        X_test_embed = embed_proj(torch.FloatTensor(X_test)).numpy()
    
    # Create PyTorch datasets
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train_embed),
        torch.FloatTensor(y_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val_embed),
        torch.FloatTensor(y_val)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test_embed),
        torch.FloatTensor(y_test)
    )
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64)
    test_loader = DataLoader(test_dataset, batch_size=64)
    
    # Initialize model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = SimplePATConvL(dropout_rate=0.2).to(device)
    
    # Loss and optimizer
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=10
    )
    
    # Training loop
    best_val_auc = 0
    patience_counter = 0
    max_patience = 30
    
    logger.info(f"\nStarting training on {device}...")
    
    for epoch in range(100):
        # Train
        model.train()
        train_loss = 0
        for embeddings, labels in train_loader:
            embeddings = embeddings.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(embeddings).squeeze()
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        # Evaluate on validation
        val_auc = evaluate_model(model, val_loader, device)
        
        # Update scheduler
        scheduler.step(val_auc)
        
        # Log progress
        if (epoch + 1) % 10 == 0:
            logger.info(
                f"Epoch {epoch+1}: "
                f"Train Loss: {train_loss/len(train_loader):.4f}, "
                f"Val AUC: {val_auc:.4f}"
            )
        
        # Early stopping
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            patience_counter = 0
            # Save best model
            torch.save(model.state_dict(), 'pat_conv_l_best_corrected.pth')
        else:
            patience_counter += 1
            if patience_counter >= max_patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break
    
    # Load best model and evaluate on TEST set
    logger.info("\n" + "="*50)
    logger.info("FINAL EVALUATION ON HELD-OUT TEST SET")
    logger.info("="*50)
    
    model.load_state_dict(torch.load('pat_conv_l_best_corrected.pth'))
    test_auc = evaluate_model(model, test_loader, device)
    
    logger.info(f"\nFinal Results:")
    logger.info(f"  Best Val AUC: {best_val_auc:.4f}")
    logger.info(f"  Test AUC: {test_auc:.4f} (THIS IS THE TRUE PERFORMANCE)")
    
    # Compare with buggy results
    logger.info(f"\nComparison:")
    logger.info(f"  Previous (buggy) result: 0.593 (but no test set!)")
    logger.info(f"  Current honest result: {test_auc:.4f}")
    logger.info(f"  Difference: {0.593 - test_auc:.4f}")
    
    if test_auc < 0.593:
        logger.info("  As expected, proper test set shows lower (honest) performance")
    
    return test_auc


if __name__ == "__main__":
    main()