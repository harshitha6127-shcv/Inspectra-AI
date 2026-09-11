"""
anomaly_detection.py - Stage 1: Defective vs Normal Anomaly Detection
====================================================================
Implements dual-approach industrial anomaly detection:
1. Unsupervised Convolutional Autoencoder (CAE):
   - Trained exclusively on normal (defect-free) parts.
   - Anomaly score derived from reconstruction error (MSE + SSIM-weighted loss).
   - Dynamic thresholding via statistical distribution (mean + k*std) or ROC-AUC optimization.
2. Supervised Transfer Learning (EfficientNet-B0 / ResNet-50):
   - Pretrained backbone fine-tuned as a high-precision binary classifier.
3. Model training loops, checkpointing, loss curve visualizer, and predict() API.
"""

import os
import json
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional, Union
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torchvision.models as models
except ImportError:
    torch = None
    nn = object
    F = None
    models = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from sklearn.metrics import roc_curve, auc, precision_recall_curve
except ImportError:
    roc_curve = None


# -------------------------------------------------------------------------
# 1. SSIM Loss Helper (Differentiable PyTorch implementation)
# -------------------------------------------------------------------------
def gaussian_window(window_size: int = 11, sigma: float = 1.5, channels: int = 3):
    """Generates 2D Gaussian kernel window for SSIM calculation."""
    if torch is None:
        return None
    coords = torch.arange(window_size).float() - window_size // 2
    g = torch.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = g / g.sum()
    window_2d = g.unsqueeze(1) @ g.unsqueeze(0)
    window = window_2d.unsqueeze(0).unsqueeze(0).repeat(channels, 1, 1, 1)
    return window


def ssim_loss(img1, img2, window_size: int = 11, val_range: float = 1.0) -> Any:
    """Computes (1.0 - SSIM) structural similarity loss."""
    if torch is None:
        return 0.0
    c = img1.size(1)
    window = gaussian_window(window_size, channels=c).to(img1.device)
    
    mu1 = F.conv2d(img1, window, padding=window_size // 2, groups=c)
    mu2 = F.conv2d(img2, window, padding=window_size // 2, groups=c)
    
    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = F.conv2d(img1 * img1, window, padding=window_size // 2, groups=c) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=window_size // 2, groups=c) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=window_size // 2, groups=c) - mu1_mu2
    
    c1 = (0.01 * val_range) ** 2
    c2 = (0.03 * val_range) ** 2
    
    ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
    return 1.0 - ssim_map.mean()


# -------------------------------------------------------------------------
# 2. Convolutional Autoencoder Architecture
# -------------------------------------------------------------------------
if torch is not None:
    class ConvAutoencoder(nn.Module):
        """
        Deep Convolutional Autoencoder designed for high-resolution industrial defect detection.
        Encodes normal structural textures into a compressed latent bottleneck.
        When defective items are passed, reconstruction error spikes in the defect region.
        """
        def __init__(self, in_channels: int = 3, base_filters: int = 32):
            super().__init__()
            # Encoder
            self.enc1 = nn.Sequential(
                nn.Conv2d(in_channels, base_filters, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 256 -> 128
            self.enc2 = nn.Sequential(
                nn.Conv2d(base_filters, base_filters * 2, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters * 2),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 128 -> 64
            self.enc3 = nn.Sequential(
                nn.Conv2d(base_filters * 2, base_filters * 4, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters * 4),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 64 -> 32
            self.enc4 = nn.Sequential(
                nn.Conv2d(base_filters * 4, base_filters * 8, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters * 8),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 32 -> 16

            # Latent Bottleneck
            self.bottleneck = nn.Sequential(
                nn.Conv2d(base_filters * 8, base_filters * 8, kernel_size=3, stride=1, padding=1),
                nn.BatchNorm2d(base_filters * 8),
                nn.LeakyReLU(0.2, inplace=True)
            )

            # Decoder
            self.dec4 = nn.Sequential(
                nn.ConvTranspose2d(base_filters * 8, base_filters * 4, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters * 4),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 16 -> 32
            self.dec3 = nn.Sequential(
                nn.ConvTranspose2d(base_filters * 4, base_filters * 2, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters * 2),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 32 -> 64
            self.dec2 = nn.Sequential(
                nn.ConvTranspose2d(base_filters * 2, base_filters, kernel_size=4, stride=2, padding=1),
                nn.BatchNorm2d(base_filters),
                nn.LeakyReLU(0.2, inplace=True)
            )  # 64 -> 128
            self.dec1 = nn.Sequential(
                nn.ConvTranspose2d(base_filters, in_channels, kernel_size=4, stride=2, padding=1),
                nn.Sigmoid()  # Normalize output pixels to [0.0, 1.0]
            )  # 128 -> 256

        def forward(self, x):
            x1 = self.enc1(x)
            x2 = self.enc2(x1)
            x3 = self.enc3(x2)
            x4 = self.enc4(x3)
            latent = self.bottleneck(x4)
            d4 = self.dec4(latent)
            d3 = self.dec3(d4)
            d2 = self.dec2(d3)
            reconstructed = self.dec1(d2)
            return reconstructed
else:
    class ConvAutoencoder:
        pass


# -------------------------------------------------------------------------
# 3. Transfer Learning Binary Classifier (Alternative Approach)
# -------------------------------------------------------------------------
if torch is not None:
    class TransferBinaryClassifier(nn.Module):
        """
        Fine-tuned Transfer Learning model (EfficientNet-B0 or ResNet-50)
        for supervised binary defect detection.
        """
        def __init__(self, backbone: str = "efficientnet_b0", pretrained: bool = True):
            super().__init__()
            if backbone == "efficientnet_b0":
                weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
                base = models.efficientnet_b0(weights=weights)
                in_features = base.classifier[1].in_features
                base.classifier = nn.Sequential(
                    nn.Dropout(p=0.3, inplace=True),
                    nn.Linear(in_features, 64),
                    nn.ReLU(inplace=True),
                    nn.Linear(64, 1)  # Logits for binary defective probability
                )
                self.model = base
            else:  # resnet50
                weights = models.ResNet50_Weights.DEFAULT if pretrained else None
                base = models.resnet50(weights=weights)
                in_features = base.fc.in_features
                base.fc = nn.Sequential(
                    nn.Dropout(p=0.3, inplace=True),
                    nn.Linear(in_features, 64),
                    nn.ReLU(inplace=True),
                    nn.Linear(64, 1)
                )
                self.model = base

        def forward(self, x):
            return self.model(x)
else:
    class TransferBinaryClassifier:
        pass


# -------------------------------------------------------------------------
# 4. Result Container & Thresholding Engine
# -------------------------------------------------------------------------
@dataclass
class AnomalyResult:
    label: str               # "normal" or "defective"
    anomaly_score: float     # Reconstruction error or predicted anomaly probability [0.0, 1.0]
    confidence: float        # Decision confidence percentage [0.0, 1.0]
    threshold: float         # Threshold used for decision
    reconstruction: Optional[np.ndarray] = None  # RGB image of CAE reconstruction
    diff_map: Optional[np.ndarray] = None        # Pixel-wise difference heatmap (uint8)


class AnomalyDetector:
    """
    Unified manager for training, evaluating, thresholding, and predicting
    industrial defects using either Autoencoder or Transfer Learning.
    """
    def __init__(
        self,
        approach: str = "autoencoder",  # "autoencoder" or "transfer_learning"
        device: Optional[str] = None,
        threshold: Optional[float] = None
    ):
        self.approach = approach
        self.device = device or ("cuda" if torch and torch.cuda.is_available() else "cpu")
        self.threshold = threshold
        self.stats = {"mean": 0.0, "std": 0.0, "k": 3.0}
        
        if torch is not None:
            if self.approach == "autoencoder":
                self.model = ConvAutoencoder().to(self.device)
            else:
                self.model = TransferBinaryClassifier(backbone="efficientnet_b0").to(self.device)
        else:
            self.model = None

    def calculate_reconstruction_error(
        self,
        x: Any,
        recon: Any,
        ssim_weight: float = 0.4
    ) -> Tuple[Any, Any]:
        """
        Calculates hybrid MSE + (1 - SSIM) reconstruction loss.
        """
        mse_pixel = F.mse_loss(recon, x, reduction="none").mean(dim=1)  # [B, H, W]
        mse_scalar = mse_pixel.mean(dim=[1, 2])                          # [B]
        
        # Batch ssim
        ssim_val = ssim_loss(recon, x)
        combined_score = (1.0 - ssim_weight) * mse_scalar + ssim_weight * ssim_val
        return combined_score, mse_pixel

    def calibrate_threshold(
        self,
        val_loader: Any,
        method: str = "mean_std",  # "mean_std" or "roc_optimal"
        k: float = 3.0
    ) -> float:
        """
        Calibrates optimal defect threshold using validation normal images.

        Methods:
        - 'mean_std': threshold = mean(errors) + k * std(errors)
        - 'roc_optimal': Maximizes Youden's J-statistic on validation set with labels.
        """
        if self.model is None or torch is None:
            self.threshold = 0.035
            return self.threshold

        self.model.eval()
        scores = []
        labels = []

        with torch.no_grad():
            for batch in val_loader:
                imgs = batch[0].to(self.device)
                lbls = batch[1] if len(batch) > 1 else torch.zeros(imgs.size(0))
                
                if self.approach == "autoencoder":
                    recon = self.model(imgs)
                    errs, _ = self.calculate_reconstruction_error(imgs, recon)
                    scores.extend(errs.cpu().numpy().tolist())
                else:
                    logits = self.model(imgs)
                    probs = torch.sigmoid(logits).squeeze(-1)
                    scores.extend(probs.cpu().numpy().tolist())
                labels.extend(lbls.numpy().tolist())

        scores = np.array(scores)
        if method == "mean_std" or len(set(labels)) < 2:
            # Assume normal data calibration
            mean = float(np.mean(scores))
            std = float(np.std(scores))
            self.threshold = mean + k * std
            self.stats = {"mean": mean, "std": std, "k": k}
            print(f"[+] Calibrated threshold (mean + {k}*std): {self.threshold:.5f} (Mean: {mean:.5f}, Std: {std:.5f})")
        else:
            if roc_curve is not None:
                fpr, tpr, thresholds = roc_curve(labels, scores)
                j_scores = tpr - fpr
                best_idx = np.argmax(j_scores)
                self.threshold = float(thresholds[best_idx])
                roc_auc = auc(fpr, tpr)
                print(f"[+] Optimal ROC threshold: {self.threshold:.5f} (ROC-AUC: {roc_auc:.4f})")

        return self.threshold

    def train_epoch_autoencoder(self, train_loader, optimizer):
        self.model.train()
        total_loss = 0.0
        for batch in train_loader:
            imgs = batch[0].to(self.device)
            optimizer.zero_grad()
            recon = self.model(imgs)
            
            # Hybrid MSE + SSIM loss
            mse = F.mse_loss(recon, imgs)
            s_loss = ssim_loss(recon, imgs)
            loss = 0.6 * mse + 0.4 * s_loss
            
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        return total_loss / len(train_loader.dataset)

    def train(
        self,
        train_loader: Any,
        val_loader: Any,
        epochs: int = 25,
        lr: float = 1e-3,
        save_path: str = "models/autoencoder_best.pth"
    ) -> Dict[str, list]:
        """
        Executes complete training loop with model checkpointing and validation tracking.
        """
        if self.model is None or torch is None:
            return {"train_loss": [], "val_loss": []}

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3)

        history = {"train_loss": [], "val_loss": []}
        best_val_loss = float("inf")

        print(f"[*] Starting training [{self.approach.upper()}] for {epochs} epochs on {self.device}...")
        for epoch in range(1, epochs + 1):
            if self.approach == "autoencoder":
                train_loss = self.train_epoch_autoencoder(train_loader, optimizer)
            else:
                # Binary classification training
                self.model.train()
                t_loss = 0.0
                for imgs, targets in train_loader:
                    imgs, targets = imgs.to(self.device), targets.float().to(self.device)
                    optimizer.zero_grad()
                    logits = self.model(imgs).squeeze(-1)
                    loss = F.binary_cross_entropy_with_logits(logits, targets)
                    loss.backward()
                    optimizer.step()
                    t_loss += loss.item() * imgs.size(0)
                train_loss = t_loss / len(train_loader.dataset)

            # Validation step
            self.model.eval()
            v_loss = 0.0
            with torch.no_grad():
                for batch in val_loader:
                    imgs = batch[0].to(self.device)
                    if self.approach == "autoencoder":
                        recon = self.model(imgs)
                        loss = 0.6 * F.mse_loss(recon, imgs) + 0.4 * ssim_loss(recon, imgs)
                    else:
                        targets = batch[1].float().to(self.device)
                        logits = self.model(imgs).squeeze(-1)
                        loss = F.binary_cross_entropy_with_logits(logits, targets)
                    v_loss += loss.item() * imgs.size(0)
            val_loss = v_loss / len(val_loader.dataset)
            scheduler.step(val_loss)

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(self.model.state_dict(), save_path)
                status_save = "*"
            else:
                status_save = ""

            print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f} {status_save}")

        # Calibrate default threshold post-training
        self.calibrate_threshold(val_loader)
        return history

    def predict(
        self,
        image: Union[np.ndarray, Any]
    ) -> AnomalyResult:
        """
        Inference function returning defect label, anomaly score, and confidence.

        Args:
            image: Preprocessed RGB or BGR numpy array [H, W, 3] in [0, 255] or float [0, 1].

        Returns:
            AnomalyResult with label ('normal' or 'defective'), anomaly_score, confidence.
        """
        # Default fallback if PyTorch not active
        if self.model is None or torch is None:
            # Fallback heuristic using image gradient variance
            gray = image.mean(axis=2) if len(image.shape) == 3 else image
            score = float(np.std(gray) / 128.0)
            thresh = self.threshold or 0.25
            is_defective = score > thresh
            conf = min(0.99, max(0.51, abs(score - thresh) / thresh))
            return AnomalyResult(
                label="defective" if is_defective else "normal",
                anomaly_score=round(score, 4),
                confidence=round(conf, 4),
                threshold=round(thresh, 4)
            )

        self.model.eval()
        # Convert numpy to normalized PyTorch tensor [1, 3, H, W]
        if isinstance(image, np.ndarray):
            img_norm = image.astype(np.float32) / 255.0 if image.max() > 1.0 else image.astype(np.float32)
            tensor = torch.from_numpy(img_norm.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
        else:
            tensor = image.to(self.device)

        thresh = self.threshold or 0.035

        with torch.no_grad():
            if self.approach == "autoencoder":
                recon = self.model(tensor)
                score_tensor, diff_map = self.calculate_reconstruction_error(tensor, recon)
                score = float(score_tensor.item())
                
                # Format reconstruction image & diff map for inspection visualizers
                recon_np = (recon.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)
                diff_np = (diff_map.squeeze(0).cpu().numpy() * 255).astype(np.uint8)
            else:
                logits = self.model(tensor)
                prob = torch.sigmoid(logits).item()
                score = float(prob)
                recon_np = None
                diff_np = None

        is_defective = score >= thresh
        # Confidence calculation relative to distance from decision threshold
        dist = abs(score - thresh) / (thresh + 1e-6)
        confidence = float(min(0.99, max(0.55, 0.5 + 0.5 * min(1.0, dist))))

        return AnomalyResult(
            label="defective" if is_defective else "normal",
            anomaly_score=round(score, 5),
            confidence=round(confidence, 4),
            threshold=round(thresh, 5),
            reconstruction=recon_np,
            diff_map=diff_np
        )


def plot_training_history(history: Dict[str, list], save_path: str = "outputs/anomaly_loss_curves.png"):
    """Plots training and validation loss curves over epochs."""
    if plt is None or not history["train_loss"]:
        return
    plt.figure(figsize=(9, 5))
    epochs = range(1, len(history["train_loss"]) + 1)
    plt.plot(epochs, history["train_loss"], "b-o", label="Training Loss")
    plt.plot(epochs, history["val_loss"], "r-s", label="Validation Loss")
    plt.title("Anomaly Detection Model — Reconstruction Loss Curve")
    plt.xlabel("Epoch")
    plt.ylabel("Loss (MSE + SSIM)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[+] Saved training history plot to {save_path}")


if __name__ == "__main__":
    print("Testing Anomaly Detector module initialization...")
    detector = AnomalyDetector(approach="autoencoder")
    dummy_img = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
    res = detector.predict(dummy_img)
    print(f"  Prediction Result: Label={res.label}, Anomaly Score={res.anomaly_score}, Confidence={res.confidence:.2%}")
