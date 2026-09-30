"""
医疗模块 PyTorch DNN/LSTM/3DCNN 模型推理封装 v2
==============================================
支持新旧模型格式自动检测, ensemble推理, 不确定性量化
"""

import os, copy, warnings
import numpy as np
import joblib
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import OrderedDict

warnings.filterwarnings('ignore')
MODELS_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ╔══════════════════════════════════════════════════════╗
# ║  1. 糖尿病风险 DNN                                  ║
# ╚══════════════════════════════════════════════════════╝

# ── v1 网络 (旧版 BatchNorm + ReLU) ──
class DiabetesDNN_v1(nn.Module):
    def __init__(self, input_dim=8, hidden_dims=None, dropout_rate=0.35):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [128, 256, 128]
        layers = []
        prev_dim = input_dim
        for hdim in hidden_dims:
            layers.extend([nn.Linear(prev_dim, hdim), nn.BatchNorm1d(hdim),
                           nn.ReLU(True), nn.Dropout(dropout_rate)])
            prev_dim = hdim
        layers.extend([nn.Linear(prev_dim, 64), nn.BatchNorm1d(64),
                       nn.ReLU(True), nn.Dropout(dropout_rate * 0.8), nn.Linear(64, 1)])
        self.network = nn.Sequential(*layers)
    def forward(self, x):
        return self.network(x)


# ── v2 网络 (改进版: ResBlock + SELU + AlphaDropout) ──
class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.fc1, self.fc2 = nn.Linear(dim, dim), nn.Linear(dim, dim)
        self.drop = nn.AlphaDropout(dropout) if dropout > 0 else nn.Identity()
        self.selu = nn.SELU()
    def forward(self, x):
        return self.selu(self.fc2(self.drop(self.selu(self.fc1(x)))) + x)

class DiabetesDNNv2(nn.Module):
    def __init__(self, input_dim=8, dropout=0.25):
        super().__init__()
        self.input_layer = nn.Sequential(OrderedDict([
            ('fc_in', nn.Linear(input_dim, 256)), ('selu_in', nn.SELU()),
            ('drop_in', nn.AlphaDropout(dropout * 0.8))]))
        # NOTE: 子模块命名必须与训练脚本 train_diabetes_dnn_v2.py 保持一致
        # (block1/block2/block3)，否则 state_dict 键名不匹配导致加载失败。
        self.res_blocks = nn.Sequential(OrderedDict([
            ('block1', ResidualBlock(256, dropout)),
            ('block2', ResidualBlock(256, dropout * 0.7)),
            ('block3', ResidualBlock(256, dropout * 0.5))]))
        self.output_layer = nn.Sequential(OrderedDict([
            ('fc_mid', nn.Linear(256, 64)), ('selu_mid', nn.SELU()),
            ('drop_mid', nn.AlphaDropout(dropout * 0.5)), ('fc_out', nn.Linear(64, 1))]))
    def forward(self, x):
        return self.output_layer(self.res_blocks(self.input_layer(x)))


class DiabetesRiskPredictor:
    """糖尿病风险预测器 (支持v1/v2/ensemble)"""
    def __init__(self):
        self.models = []
        self.scaler = None
        self.opt_threshold = 0.5
        self.is_loaded = False

        model_path = os.path.join(MODELS_DIR, 'diabetes_dnn_model.pth')
        ensemble_path = os.path.join(MODELS_DIR, 'diabetes_ensemble.pth')
        scaler_path = os.path.join(MODELS_DIR, 'diabetes_scaler.joblib')

        try:
            # 加载标准化器
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)

            # 尝试加载ensemble (v2)
            if os.path.exists(ensemble_path):
                ckpt = torch.load(ensemble_path, map_location=DEVICE, weights_only=False)
                for state in ckpt['states']:
                    model = DiabetesDNNv2(input_dim=ckpt['input_dim'],
                                          dropout=ckpt.get('dropout', 0.15)).to(DEVICE)
                    model.load_state_dict(state)
                    model.eval()
                    self.models.append(model)
                self.opt_threshold = ckpt.get('opt_threshold', 0.5)
                print(f"[Diabetes] 加载v2 ensemble: {len(self.models)} models, threshold={self.opt_threshold:.3f}")

            # 尝试加载单模型 (v1或v2)
            if not self.models and os.path.exists(model_path):
                ckpt = torch.load(model_path, map_location=DEVICE, weights_only=False)
                arch = ckpt.get('architecture', '')
                input_dim = ckpt.get('input_dim', 8)

                if 'v2' in arch or 'ResBlock' in arch:
                    model = DiabetesDNNv2(input_dim=input_dim,
                                          dropout=ckpt.get('dropout', 0.15)).to(DEVICE)
                else:
                    model = DiabetesDNN_v1(input_dim=input_dim,
                                           hidden_dims=ckpt.get('hidden_layers', [128, 256, 128]),
                                           dropout_rate=ckpt.get('dropout', 0.175)).to(DEVICE)

                model.load_state_dict(ckpt['model_state_dict'])
                model.eval()
                self.models.append(model)
                self.opt_threshold = ckpt.get('opt_threshold', 0.5)
                print(f"[Diabetes] 加载单模型: {arch or 'v1'}")

            self.is_loaded = len(self.models) > 0

        except Exception as e:
            print(f"[Diabetes] 加载失败: {e}")

    @torch.no_grad()
    def predict(self, features, mc_samples=1):
        if not self.is_loaded:
            return {'risk_probability': 0.5, 'risk_level': 'unknown', 'error': 'model not loaded'}

        features = np.array(features, dtype=np.float32).reshape(1, -1)
        if self.scaler is not None:
            scaled = self.scaler.transform(features)
        else:
            scaled = features

        # Ensemble + MC Dropout推理
        all_preds = []
        for model in self.models:
            model.train()  # 启用Dropout
            x = torch.FloatTensor(scaled).to(DEVICE)
            for _ in range(mc_samples):
                out = torch.sigmoid(model(x)).cpu().numpy().flatten()[0]
                all_preds.append(out)

        all_preds = np.array(all_preds)
        prob = float(all_preds.mean())
        uncertainty = float(all_preds.std())

        # 风险等级 (使用最优阈值)
        if prob < self.opt_threshold - 0.15:
            risk_level, risk_label, advice = 'low', '低风险', (
                '您的糖尿病风险较低。建议保持健康生活方式，定期体检。')
        elif prob < self.opt_threshold + 0.15:
            risk_level, risk_label, advice = 'medium', '中风险', (
                '您的糖尿病风险处于中等水平。建议控制饮食、增加运动、定期监测血糖。')
        else:
            risk_level, risk_label, advice = 'high', '高风险', (
                '您的糖尿病风险较高! 强烈建议尽快就医，进行口服葡萄糖耐量试验(OGTT)筛查。')

        return {
            'risk_probability': round(prob, 4),
            'risk_percentage': round(prob * 100, 1),
            'uncertainty': round(uncertainty, 4),
            'risk_level': risk_level,
            'risk_label': risk_label,
            'health_advice': advice,
            'model_type': f'PyTorch DNN Ensemble ({len(self.models)} models)',
        }


# ╔══════════════════════════════════════════════════════╗
# ║  2. 血糖预测 LSTM / Transformer                      ║
# ╚══════════════════════════════════════════════════════╝

# ── v1 BiLSTM ──
class GlucoseBiLSTM_v1(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=2,
                 dropout=0.3, output_steps=1):
        super().__init__()
        self.output_steps = output_steps
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True,
                            dropout=dropout if num_layers > 1 else 0, bidirectional=True)
        lstm_out = hidden_size * 2
        self.attention = nn.Sequential(
            nn.Linear(lstm_out, 64), nn.Tanh(), nn.Linear(64, 1), nn.Softmax(dim=1))
        self.regressor = nn.Sequential(
            nn.Linear(lstm_out, 64), nn.ReLU(), nn.Dropout(dropout * 0.5),
            nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, output_steps))

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn = self.attention(lstm_out)
        context = torch.sum(attn * lstm_out, dim=1)
        return self.regressor(context)


# ── v2 BiLSTM ──
class GlucoseBiLSTM_v2(nn.Module):
    def __init__(self, input_size=1, hidden_size=128, num_layers=3,
                 dropout=0.15, seq_len=24, pred_len=12, use_attention=True):
        super().__init__()
        self.pred_len = pred_len
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True,
                            bidirectional=True, dropout=dropout)
        lstm_out = hidden_size * 2
        self.use_attention = use_attention
        if use_attention:
            self.attention = nn.MultiheadAttention(lstm_out, 4, batch_first=True, dropout=dropout)
        # NOTE: 结构/命名必须与训练脚本 train_glucose_transformer_v2.py 的
        # GlucoseBiLSTM 保持一致（attention_proj + fc.fc1/fc2），
        # 否则 glucose_lstm_*.pth 的 state_dict 无法加载。
        self.attention_proj = nn.Linear(lstm_out, lstm_out // 2)
        self.fc = nn.Sequential(OrderedDict([
            ('fc1', nn.Linear(lstm_out // 2, 64)),
            ('gelu', nn.GELU()),
            ('drop', nn.Dropout(dropout)),
            ('fc2', nn.Linear(64, pred_len)),
        ]))

    def forward(self, x):
        out, _ = self.lstm(x)
        if self.use_attention:
            attn_out, _ = self.attention(out, out, out)
            out = out + attn_out
        pooled = out.mean(dim=1)
        return self.fc(self.attention_proj(pooled))


# ── v2 Transformer ──
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=500):
        super().__init__()
        self.pos = nn.Parameter(torch.randn(1, max_len, d_model) * 0.1)
    def forward(self, x):
        return x + self.pos[:, :x.size(1), :]

class GlucoseTransformer(nn.Module):
    def __init__(self, seq_len=24, pred_30=6, pred_60=12,
                 d_model=128, nhead=8, num_layers=4, dropout=0.15, n_patients=9):
        super().__init__()
        self.seq_len, self.d_model = seq_len, d_model
        self.input_proj = nn.Linear(1, d_model)
        self.pos_encoder = PositionalEncoding(d_model, seq_len)
        self.patient_emb = nn.Embedding(n_patients, d_model)
        enc_layer = nn.TransformerEncoderLayer(
            d_model, nhead, d_model * 4, dropout, batch_first=True, activation='gelu')
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers)
        self.time_encoder = nn.Sequential(
            nn.Linear(2, d_model // 4), nn.GELU(), nn.Linear(d_model // 4, d_model))
        self.output_proj = nn.Sequential(
            nn.Linear(d_model, d_model // 2), nn.GELU(), nn.Dropout(dropout))
        self.head_30min = nn.Linear(d_model // 2, pred_30)
        self.head_60min = nn.Linear(d_model // 2, pred_60)

    def forward(self, x, patient_ids=None, time_feats=None):
        B, S = x.shape[0], x.shape[1]
        x = self.pos_encoder(self.input_proj(x))
        if time_feats is not None:
            x = x + self.time_encoder(time_feats)
        if patient_ids is not None:
            x = x + self.patient_emb(patient_ids).unsqueeze(1)
        x = self.transformer(x)[:, -1, :]
        x = self.output_proj(x)
        return self.head_30min(x), self.head_60min(x)


class GlucoseForecastPredictor:
    """血糖时序预测器 (支持v1/v2 LSTM, Transformer)"""
    def __init__(self):
        self.device = DEVICE
        self.models = {'30min': None, '60min': None}
        self.scaler = None
        self.lookback = 12
        self.is_loaded = False
        self.model_type = 'unknown'

        model_paths = {
            '30min': os.path.join(MODELS_DIR, 'glucose_lstm_30min.pth'),
            '60min': os.path.join(MODELS_DIR, 'glucose_lstm_60min.pth'),
        }
        scaler_path = os.path.join(MODELS_DIR, 'glucose_scaler.joblib')

        try:
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)

            for name, path in model_paths.items():
                if not os.path.exists(path):
                    continue

                ckpt = torch.load(path, map_location=self.device, weights_only=False)
                model_type = ckpt.get('model_type', 'GlucoseBiLSTM')

                if model_type == 'GlucoseTransformer':
                    cfg = ckpt['config']
                    model = GlucoseTransformer(
                        seq_len=cfg['seq_len'], pred_30=cfg['pred_30'],
                        pred_60=cfg['pred_60'], d_model=cfg['d_model'],
                        nhead=cfg['nhead'], num_layers=cfg['num_layers'],
                        dropout=cfg['dropout'], n_patients=cfg.get('n_patients', 9))
                    self.lookback = cfg['seq_len']
                    self.model_type = 'GlucoseTransformer'
                elif model_type == 'GlucoseBiLSTM':
                    cfg = ckpt['config']
                    model = GlucoseBiLSTM_v2(
                        input_size=cfg.get('input_size', 1),
                        hidden_size=cfg.get('hidden_size', 128),
                        num_layers=cfg.get('num_layers', 3),
                        dropout=cfg.get('dropout', 0.15),
                        seq_len=cfg.get('seq_len', 24),
                        pred_len=cfg.get('pred_len', 12))
                    self.lookback = cfg.get('seq_len', 24)
                    self.model_type = 'GlucoseBiLSTM_v2'
                else:
                    # v1 fallback
                    model = GlucoseBiLSTM_v1(
                        input_size=ckpt.get('input_size', 1),
                        hidden_size=ckpt.get('hidden_size', 128),
                        num_layers=ckpt.get('num_layers', 2),
                        dropout=ckpt.get('dropout', 0.3),
                        output_steps=ckpt.get('output_steps', 1))
                    self.lookback = ckpt.get('lookback', 12)
                    model.y_mean = ckpt.get('y_mean', 0)
                    model.y_std = ckpt.get('y_std', 1)
                    self.model_type = 'GlucoseBiLSTM_v1'

                model.load_state_dict(ckpt['state_dict'] if 'state_dict' in ckpt
                                      else ckpt['model_state_dict'])
                model.to(self.device)
                model.eval()
                self.models[name] = model

            self.is_loaded = all(v is not None for v in self.models.values())
            if self.is_loaded:
                print(f"[Glucose] 加载 {self.model_type}: lookback={self.lookback}")

        except Exception as e:
            print(f"[Glucose] 加载失败: {e}")

    @torch.no_grad()
    def predict(self, readings, predict_minutes=30):
        if not self.is_loaded:
            return {'forecast_glucose': None, 'error': 'model not loaded'}

        model_key = '30min' if predict_minutes == 30 else '60min'
        model = self.models.get(model_key)
        if model is None:
            return {'forecast_glucose': None, 'error': f'unsupported: {predict_minutes}min'}

        readings = np.array(readings[-self.lookback:], dtype=np.float32)
        if len(readings) < self.lookback:
            return {'forecast_glucose': None, 'error': f'need {self.lookback} readings, got {len(readings)}'}

        # 标准化
        if self.scaler is not None:
            x = self.scaler.transform(readings.reshape(-1, 1)).ravel()
        else:
            x = (readings - np.mean(readings)) / (np.std(readings) + 1e-8)

        x_tensor = torch.FloatTensor(x).view(1, -1, 1).to(self.device)
        out = model(x_tensor)
        if isinstance(out, tuple):  # GlucoseTransformer 返回 (pred_30, pred_60)
            out = out[0] if predict_minutes == 30 else out[1]
        pred = out.cpu().numpy().flatten()

        # 目标值反标准化：
        # - v1 BiLSTM 训练时对 y 做了标准化 → 用 y_mean/y_std 还原
        # - v2 (BiLSTM/Transformer) 训练时 y 为原始血糖值(mmol/L)
        #   （训练脚本 GlucoseDataset 仅对 X 做 RobustScaler，目标未标准化）
        #   → 直接使用，绝不可再 inverse_transform，否则会被放大数百倍
        if hasattr(model, 'y_mean'):
            pred = pred * model.y_std + model.y_mean

        # 预测值 = 序列最后一个预测点
        forecast = float(pred[-1] if len(pred) > 1 else pred[0])
        current = float(readings[-1])
        change = forecast - current

        # 趋势判断
        if change > 0.5:
            trend, trend_label = 'rapid_rise', '快速上升'
        elif change > 0.2:
            trend, trend_label = 'rise', '缓慢上升'
        elif change < -0.5:
            trend, trend_label = 'rapid_fall', '快速下降'
        elif change < -0.2:
            trend, trend_label = 'fall', '缓慢下降'
        else:
            trend, trend_label = 'stable', '平稳'

        # 警报
        alert = None
        if forecast < 3.9:
            alert = {'level': 'danger', 'type': 'hypoglycemia',
                     'message': f'预测血糖 {forecast:.1f} mmol/L, 低于正常值(3.9), 可能发生低血糖!'}
        elif forecast > 11.1:
            alert = {'level': 'danger', 'type': 'hyperglycemia',
                     'message': f'预测血糖 {forecast:.1f} mmol/L, 高于诊断标准(11.1), 请注意!'}
        elif forecast > 7.0:
            alert = {'level': 'warning', 'type': 'elevated',
                     'message': f'预测血糖 {forecast:.1f} mmol/L, 偏高。'}

        # 图表数据
        chart_data = []
        for i, v in enumerate(readings):
            chart_data.append({
                'time': f'T-{(self.lookback - i) * 5}',
                'value': float(v), 'type': 'history'})
        chart_data.append({
            'time': f'T+{predict_minutes}',
            'value': round(forecast, 1), 'type': 'forecast'})

        # 预测序列 (完整预测曲线)
        pred_seq = [float(v) for v in pred]
        forecast_curve = []
        for i, v in enumerate(pred_seq):
            forecast_curve.append({
                'time': f'T+{(i + 1) * 5}',
                'value': round(v, 1)})

        return {
            'current_glucose': round(current, 1),
            'forecast_glucose': round(forecast, 1),
            'change': round(change, 1),
            'trend': trend,
            'trend_label': trend_label,
            'alert': alert,
            'chart_data': chart_data,
            'forecast_curve': forecast_curve,
            'model_type': self.model_type,
        }


# ╔══════════════════════════════════════════════════════╗
# ║  3. 脑部CT 3D 自编码器                              ║
# ╚══════════════════════════════════════════════════════╝

class Conv3DBlock(nn.Module):
    def __init__(self, in_ch, out_ch, k=3, s=1, p=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, k, s, p, bias=False),
            nn.BatchNorm3d(out_ch), nn.LeakyReLU(0.2))
    def forward(self, x):
        return self.conv(x)

# ── v1 自编码器 ──
class CT3DAutoencoder(nn.Module):
    def __init__(self, base_ch=32, latent_dim=256):
        super().__init__()
        self.encoder = nn.Sequential(
            Conv3DBlock(1, base_ch, 3, 2, 1),
            Conv3DBlock(base_ch, base_ch*2, 3, 2, 1),
            Conv3DBlock(base_ch*2, base_ch*4, 3, 2, 1),
            Conv3DBlock(base_ch*4, base_ch*8, 3, 2, 1))
        self.fc_enc = nn.Linear(base_ch*8*2*2*2, latent_dim)
        self.drop = nn.Dropout(0.2)
        self.fc_dec = nn.Linear(latent_dim, base_ch*8*2*2*2)
        self.decoder = nn.Sequential(
            nn.ConvTranspose3d(base_ch*8, base_ch*4, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_ch*4), nn.LeakyReLU(0.2),
            nn.ConvTranspose3d(base_ch*4, base_ch*2, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_ch*2), nn.LeakyReLU(0.2),
            nn.ConvTranspose3d(base_ch*2, base_ch, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_ch), nn.LeakyReLU(0.2),
            nn.ConvTranspose3d(base_ch, 1, 4, 2, 1, bias=False))

    def forward(self, x):
        z = self.fc_enc(self.encoder(x).view(x.size(0), -1))
        z = self.drop(z)
        z = self.fc_dec(z).view(z.size(0), 256, 2, 2, 2)
        return self.decoder(z), None


# ── v2 3D ResNet Autoencoder ──
class Conv3DResBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, stride, 1, bias=False), nn.BatchNorm3d(out_ch), nn.LeakyReLU(0.2, True),
            nn.Conv3d(out_ch, out_ch, 3, 1, 1, bias=False), nn.BatchNorm3d(out_ch))
        self.short = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.short = nn.Sequential(nn.Conv3d(in_ch, out_ch, 1, stride, bias=False), nn.BatchNorm3d(out_ch))
    def forward(self, x):
        return F.leaky_relu(self.conv(x) + self.short(x), 0.2, True)

class UpConv3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_ch, out_ch, 2, 2)
        self.conv = Conv3DResBlock(out_ch * 2, out_ch)
    def forward(self, x, skip):
        x = self.up(x)
        if x.shape[-3:] != skip.shape[-3:]:
            d = [skip.shape[-3] - x.shape[-3], skip.shape[-2] - x.shape[-2], skip.shape[-1] - x.shape[-1]]
            x = F.pad(x, [d[2]//2, d[2]-d[2]//2, d[1]//2, d[1]-d[1]//2, d[0]//2, d[0]-d[0]//2])
        return self.conv(torch.cat([x, skip], 1))

class ResNet3DAE(nn.Module):
    def __init__(self, in_channels=1, base_ch=32):
        super().__init__()
        self.enc_conv1 = nn.Sequential(
            nn.Conv3d(in_channels, base_ch, 7, 2, 3, bias=False), nn.BatchNorm3d(base_ch),
            nn.LeakyReLU(0.2, True), nn.MaxPool3d(3, 2, 1))
        self.enc_l1 = self._make_layer(base_ch, base_ch*2, 2, 2)
        self.enc_l2 = self._make_layer(base_ch*2, base_ch*4, 2, 2)
        self.enc_l3 = self._make_layer(base_ch*4, base_ch*8, 2, 2)
        self.enc_l4 = self._make_layer(base_ch*8, base_ch*16, 2, 2)
        self.bottleneck = nn.Sequential(
            nn.Conv3d(base_ch*16, base_ch*16, 3, 1, 1, bias=False), nn.BatchNorm3d(base_ch*16), nn.LeakyReLU(0.2, True),
            nn.Conv3d(base_ch*16, base_ch*8, 1, 1, bias=False), nn.BatchNorm3d(base_ch*8), nn.LeakyReLU(0.2, True))
        self.dec_l4 = UpConv3D(base_ch*8, base_ch*4)
        self.dec_l3 = UpConv3D(base_ch*4, base_ch*2)
        self.dec_l2 = UpConv3D(base_ch*2, base_ch)
        self.dec_l1 = UpConv3D(base_ch, base_ch//2)
        self.out_conv = nn.Sequential(
            nn.ConvTranspose3d(base_ch//2, base_ch//2, 2, 2), nn.BatchNorm3d(base_ch//2),
            nn.LeakyReLU(0.2, True), nn.Conv3d(base_ch//2, 1, 3, 1, 1))
    def _make_layer(self, in_ch, out_ch, n, stride=1):
        layers = [Conv3DResBlock(in_ch, out_ch, stride)]
        for _ in range(1, n):
            layers.append(Conv3DResBlock(out_ch, out_ch))
        return nn.Sequential(*layers)
    def encode(self, x):
        skips = [x := self.enc_conv1(x)]
        skips.append(x := self.enc_l1(x))
        skips.append(x := self.enc_l2(x))
        skips.append(x := self.enc_l3(x))
        skips.append(x := self.enc_l4(x))
        return self.bottleneck(x), skips
    def decode(self, x, skips):
        x = self.dec_l4(x, skips[3])
        x = self.dec_l3(x, skips[2])
        x = self.dec_l2(x, skips[1])
        x = self.dec_l1(x, skips[0])
        return self.out_conv(x)
    def forward(self, x):
        z, skips = self.encode(x)
        return self.decode(z, skips)


class BrainCTDetector:
    """脑部CT异常检测器 (支持v1/v2)"""
    def __init__(self):
        self.device = DEVICE
        self.model = None
        self.info = None
        self.is_loaded = False

        # 尝试v2
        model_paths = [
            os.path.join(MODELS_DIR, 'brain_ct_ae.pth'),           # v2
            os.path.join(MODELS_DIR, 'brain_ct_3d_ae.pth'),        # old name
        ]
        info_path = os.path.join(MODELS_DIR, 'brain_ct_info.joblib')

        for model_path in model_paths:
            if os.path.exists(model_path):
                try:
                    ckpt = torch.load(model_path, map_location=self.device, weights_only=False)
                    arch = ckpt.get('architecture', '')

                    if 'ResNet3DAE' in arch:
                        self.model = ResNet3DAE(1, ckpt.get('config', {}).get('base_channels', 32))
                        self.model.load_state_dict(ckpt['model_state_dict'])
                        self.patch_size = ckpt.get('config', {}).get('patch_size', 48)
                        self.anomaly_threshold = ckpt.get('performance', {}).get('best_val_loss', 0.02)
                        print(f"[BrainCT] 加载v2 ResNet3DAE")
                    else:
                        self.model = CT3DAutoencoder(
                            base_ch=ckpt.get('base_channels', 32),
                            latent_dim=ckpt.get('latent_dim', 256))
                        if 'model_state_dict' in ckpt:
                            self.model.load_state_dict(ckpt['model_state_dict'])
                        else:
                            self.model.load_state_dict(ckpt)
                        self.patch_size = ckpt.get('patch_size', 32)
                        self.anomaly_threshold = ckpt.get('anomaly_threshold', 0.05)
                        print(f"[BrainCT] 加载v1 CT3DAutoencoder")

                    self.model.to(self.device)
                    self.model.eval()

                    if os.path.exists(info_path):
                        self.info = joblib.load(info_path)
                        self.anomaly_threshold = self.info.get('detection', {}).get('anomaly_threshold',
                                                                                    self.anomaly_threshold)

                    self.is_loaded = True
                    break
                except Exception as e:
                    print(f"[BrainCT] 加载 {os.path.basename(model_path)} 失败: {e}")
                    continue

    def analyze(self, ct_slices):
        if not self.is_loaded:
            return {'status': 'error', 'message': 'model not loaded'}

        ct_slices = np.array(ct_slices, dtype=np.float32)
        if ct_slices.ndim == 2:
            ct_slices = ct_slices[np.newaxis, ...]

        Z, H, W = ct_slices.shape
        center, width = 40, 80
        low, high = center - width/2, center + width/2
        patch_size = min(self.patch_size, Z, H, W)
        stride = max(patch_size // 2, 1)

        anomaly_scores = []
        patch_coords = []
        criterion = nn.L1Loss(reduction='none')

        with torch.no_grad():
            zs = range(0, max(1, Z - patch_size + 1), stride) if Z >= patch_size else [0]
            hs = range(0, max(1, H - patch_size + 1), stride) if H >= patch_size else [0]
            ws = range(0, max(1, W - patch_size + 1), stride) if W >= patch_size else [0]

            for z in zs:
                for h in hs:
                    for w in ws:
                        ze = min(z + patch_size, Z)
                        he = min(h + patch_size, H)
                        we = min(w + patch_size, W)

                        # 处理边缘不足patch_size的情况: mirror pad
                        patch = ct_slices[z:ze, h:he, w:we]
                        if patch.max() < -500 or patch.min() > 2000:
                            continue

                        # Pad to patch_size
                        pZ, pH, pW = patch.shape
                        pad = ((0, max(0, patch_size - pZ)), (0, max(0, patch_size - pH)),
                               (0, max(0, patch_size - pW)))
                        if any(p[1] > 0 for p in pad):
                            patch = np.pad(patch, pad, mode='reflect')

                        # 归一化到 [0, 1]
                        p_clip = np.clip(patch, low, high)
                        p_norm = (p_clip - low) / (high - low)
                        p_norm = np.clip(p_norm, 0, 1)

                        x = torch.FloatTensor(p_norm).unsqueeze(0).unsqueeze(0).to(self.device)
                        recon = self.model(x)
                        score = float(criterion(recon, x).mean().cpu().numpy())

                        anomaly_scores.append(score)
                        patch_coords.append((z, h, w))

        if not anomaly_scores:
            return {'status': 'success', 'slices_analyzed': Z, 'patches_analyzed': 0,
                    'is_abnormal': False, 'message': '未找到有效CT组织区域'}

        scores = np.array(anomaly_scores)
        max_score, mean_score = float(scores.max()), float(scores.mean())
        p95_score = float(np.percentile(scores, 95))
        is_abnormal = max_score > self.anomaly_threshold

        abnormal_patches = []
        if is_abnormal:
            for idx in np.argsort(-scores)[:5]:
                z, h, w = patch_coords[idx]
                abnormal_patches.append({
                    'z': int(z), 'h': int(h), 'w': int(w),
                    'anomaly_score': float(scores[idx]),
                    'position': f'slice {z}, row {h}, col {w}'})

        return {
            'status': 'success',
            'slices_analyzed': Z,
            'patches_analyzed': len(scores),
            'is_abnormal': is_abnormal,
            'max_anomaly_score': round(max_score, 6),
            'mean_anomaly_score': round(mean_score, 6),
            'p95_anomaly_score': round(p95_score, 6),
            'threshold': round(self.anomaly_threshold, 6),
            'abnormal_patches': abnormal_patches,
            'anomaly_percentage': round(float((scores > self.anomaly_threshold).mean() * 100), 1),
            'model_type': 'PyTorch 3D ResNet-AE' if hasattr(self.model, 'encode') else 'PyTorch 3D Autoencoder',
            'disclaimer': '本检测结果由AI辅助生成，仅供参考，请以专业医生的诊断为准。',
        }


# ╔══════════════════════════════════════════════════════╗
# ║  工厂函数 (单例)                                     ║
# ╚══════════════════════════════════════════════════════╝

_predictors = {}

def get_diabetes_predictor():
    if 'diabetes' not in _predictors:
        _predictors['diabetes'] = DiabetesRiskPredictor()
    return _predictors['diabetes']

def get_glucose_predictor():
    if 'glucose' not in _predictors:
        _predictors['glucose'] = GlucoseForecastPredictor()
    return _predictors['glucose']

def get_brain_ct_detector():
    if 'brain_ct' not in _predictors:
        _predictors['brain_ct'] = BrainCTDetector()
    return _predictors['brain_ct']
