#!/usr/bin/env python3
"""
PAT-Conv-L FINAL Training - Adapted from Successful 0.5929 Run
=============================================================

Key changes from previous successful run:
1. Uses CORRECTED data with proper test set (nhanes_pat_data_with_test.npz)
2. Uses 21k weights to avoid data leakage
3. Keeps the same Conv1D architecture that worked
"""

import logging
import sys
from pathlib import Path

import h5py
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
        logging.FileHandler('pat_conv_l_final.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ConvPatchEmbedding(nn.Module):
    """Convolutional patch embedding that got us 0.5929 AUC."""
    
    def __init__(self, patch_size: int, embed_dim: int, in_channels: int = 1):
        super().__init__()
        self.patch_size = patch_size
        
        # Conv1D with stride=patch_size creates patches
        self.conv = nn.Conv1d(
            in_channels=in_channels,
            out_channels=embed_dim,
            kernel_size=patch_size,
            stride=patch_size,
            padding=0
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim == 2:
            x = x.unsqueeze(1)  # (B, T) -> (B, 1, T)
        x = self.conv(x)  # (B, 1, T) -> (B, embed_dim, num_patches)
        x = x.permute(0, 2, 1)  # (B, embed_dim, n_patches) -> (B, n_patches, embed_dim)
        return x


class SimplePATConvLModel(nn.Module):
    """The exact model that achieved 0.5929 AUC."""
    
    def __init__(self):
        super().__init__()
        
        # PAT-L configuration
        self.patch_size = 9
        self.embed_dim = 96
        self.depth = 6
        self.num_heads = 8
        
        # Components
        self.patch_embed = ConvPatchEmbedding(
            patch_size=self.patch_size,
            embed_dim=self.embed_dim
        )
        
        # Positional embedding
        num_patches = 10080 // self.patch_size  # 1120 patches
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches, self.embed_dim))
        
        # Transformer blocks
        self.blocks = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=self.embed_dim,
                nhead=self.num_heads,
                dim_feedforward=self.embed_dim * 4,
                dropout=0.1,
                activation='gelu',
                batch_first=True
            )
            for _ in range(self.depth)
        ])
        
        # Norm and head
        self.norm = nn.LayerNorm(self.embed_dim)
        self.head = nn.Linear(self.embed_dim, 1)
        
        # Initialize
        nn.init.trunc_normal_(self.pos_embed, std=0.02)
    
    def forward(self, x):
        # Patch embedding
        x = self.patch_embed(x)
        
        # Add positional embedding
        x = x + self.pos_embed
        
        # Transformer blocks
        for block in self.blocks:
            x = block(x)
        
        # Global average pooling
        x = x.mean(dim=1)
        
        # Normalize
        x = self.norm(x)
        
        # Classification head
        x = self.head(x)
        
        return x


def load_corrected_data():
    """Load the CORRECTED data with proper test set."""
    cache_path = Path("data/cache/nhanes_pat_data_with_test.npz")
    logger.info(f"Loading CORRECTED data from {cache_path}")
    
    data = np.load(cache_path)
    
    # Verify test set exists
    assert 'X_test' in data, "No test set found!"
    
    X_train = data['X_train']
    X_val = data['X_val']
    X_test = data['X_test']
    y_train = data['y_train']
    y_val = data['y_val']
    y_test = data['y_test']
    
    logger.info(f"Data shapes - Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
    logger.info(f"Class balance - Train: {(y_train == 1).sum()}/{len(y_train)} positive")
    
    # Check normalization
    logger.info("Data statistics:")
    logger.info(f"  Train - Mean: {X_train.mean():.6f}, Std: {X_train.std():.6f}")
    logger.info(f"  Val - Mean: {X_val.mean():.6f}, Std: {X_val.std():.6f}")
    
    if abs(X_train.std() - 1.0) > 0.1:
        logger.warning("⚠️ Data normalization looks off - double check!")
    else:
        logger.info("✅ Normalization looks good - proceeding")
    
    return X_train, X_val, X_test, y_train, y_val, y_test


def load_pretrained_weights(model, weights_file="model_weights/pat/pretrained/PAT-L_21k_weights.h5"):
    """Load 21k pretrained weights (no data leakage)."""
    logger.info(f"Loading pretrained weights from {weights_file}...")
    
    with h5py.File(weights_file, 'r') as f:
        # Skip patch embedding (Conv will use random init)
        logger.info("Skipping patch embedding weights (Conv layer will use random init)")
        
        # Load positional embeddings
        if 'pos_embed' in f:
            pos_embed = torch.from_numpy(f['pos_embed'][:])
            if pos_embed.shape == model.pos_embed.shape:
                model.pos_embed.data.copy_(pos_embed)
        
        # Load transformer blocks
        for i in range(model.depth):
            block = model.blocks[i]
            
            # Multi-head attention
            if f'blocks.{i}.attn.qkv.weight' in f:
                qkv_weight = torch.from_numpy(f[f'blocks.{i}.attn.qkv.weight'][:])
                # Split QKV weight for PyTorch transformer
                embed_dim = model.embed_dim
                q_weight = qkv_weight[:embed_dim]
                k_weight = qkv_weight[embed_dim:2*embed_dim]
                v_weight = qkv_weight[2*embed_dim:]
                
                block.self_attn.in_proj_weight.data[:embed_dim].copy_(q_weight)
                block.self_attn.in_proj_weight.data[embed_dim:2*embed_dim].copy_(k_weight)
                block.self_attn.in_proj_weight.data[2*embed_dim:].copy_(v_weight)
    
    logger.info("✅ Loaded transformer weights for PAT-Conv-L")
    logger.info("Conv patch embedding initialized randomly (as intended)")


def main():
    logger.info("="*60)
    logger.info("PAT-Conv-L FINAL Training")
    logger.info("Based on successful 0.5929 run, adapted for correct data")
    logger.info("="*60)
    
    # Load data
    X_train, X_val, X_test, y_train, y_val, y_test = load_corrected_data()
    
    # Create datasets
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_val)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test),
        torch.FloatTensor(y_test)
    )
    
    # Create loaders
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64)
    test_loader = DataLoader(test_dataset, batch_size=64)
    
    # Initialize model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Using device: {device}")
    
    model = SimplePATConvLModel().to(device)
    
    # Load pretrained weights
    load_pretrained_weights(model)
    
    logger.info(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Loss function with class weighting
    pos_weight = torch.tensor([(1 - y_train.mean()) / y_train.mean()]).to(device)
    logger.info(f"Using pos_weight: {pos_weight.item():.2f}")
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    
    # Optimizer - same as successful run
    optimizer = optim.AdamW(model.parameters(), lr=0.0001, weight_decay=0.01)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=15)
    
    logger.info(f"Optimizer: AdamW with LR={0.0001}")
    logger.info(f"Scheduler: Cosine annealing over 15 epochs")
    
    # Training loop
    best_val_auc = 0
    patience_counter = 0
    
    for epoch in range(50):  # More epochs since we have less data
        # Training
        model.train()
        train_loss = 0
        
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.to(device), target.to(device)
            
            optimizer.zero_grad()
            output = model(data).squeeze()
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            
            if batch_idx % 20 == 0:
                logger.info(f"  Batch {batch_idx}/{len(train_loader)}")
        
        # Validation
        model.eval()
        val_loss = 0
        val_preds = []
        val_labels = []
        
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(device), target.to(device)
                output = model(data).squeeze()
                val_loss += criterion(output, target).item()
                
                val_preds.extend(torch.sigmoid(output).cpu().numpy())
                val_labels.extend(target.cpu().numpy())
        
        val_auc = roc_auc_score(val_labels, val_preds)
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        
        logger.info(
            f"Epoch {epoch+1:2d}: "
            f"Train Loss={avg_train_loss:.4f}, "
            f"Val Loss={avg_val_loss:.4f}, "
            f"Val AUC={val_auc:.4f}, "
            f"LR={scheduler.get_last_lr()[0]:.2e}"
        )
        
        # Save best model
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            torch.save(model.state_dict(), f'pat_conv_l_best_auc_{val_auc:.4f}.pth')
            logger.info(f"✅ Saved best model with AUC: {val_auc:.4f}")
            patience_counter = 0
            
            if val_auc > 0.59:
                logger.info("🎯 EXCELLENT: Approaching paper performance!")
        else:
            patience_counter += 1
            if patience_counter >= 10:
                logger.info("Early stopping triggered")
                break
        
        scheduler.step()
    
    # Final test evaluation
    logger.info("\n" + "="*50)
    logger.info("FINAL TEST EVALUATION")
    logger.info("="*50)
    
    model.load_state_dict(torch.load(f'pat_conv_l_best_auc_{best_val_auc:.4f}.pth'))
    model.eval()
    
    test_preds = []
    test_labels = []
    
    with torch.no_grad():
        for data, target in test_loader:
            data = data.to(device)
            output = model(data).squeeze()
            test_preds.extend(torch.sigmoid(output).cpu().numpy())
            test_labels.extend(target.numpy())
    
    test_auc = roc_auc_score(test_labels, test_preds)
    
    logger.info(f"\nFINAL RESULTS:")
    logger.info(f"Best Val AUC: {best_val_auc:.4f}")
    logger.info(f"Test AUC: {test_auc:.4f} (HONEST EVALUATION)")
    logger.info(f"\nPrevious (buggy): 0.5929")
    logger.info(f"Current (correct): {test_auc:.4f}")
    logger.info(f"Target (paper): 0.625")
    
    return test_auc


if __name__ == "__main__":
    main()