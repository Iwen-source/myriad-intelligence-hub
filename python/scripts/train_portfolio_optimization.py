"""
Portfolio Optimization: Mean-Variance (Markowitz) + Monte Carlo simulation
Generates: asset_data.joblib
"""

import numpy as np
import pandas as pd
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

ASSET_CLASSES = [
    "沪深300ETF", "中证500ETF", "国债ETF", "企业债ETF",
    "黄金ETF", "货币基金"
]

# Realistic-ish annual returns and volatilities
ASSET_PARAMS = {
    "沪深300ETF": {"mu": 0.10, "sigma": 0.20},
    "中证500ETF": {"mu": 0.12, "sigma": 0.25},
    "国债ETF": {"mu": 0.035, "sigma": 0.05},
    "企业债ETF": {"mu": 0.05, "sigma": 0.08},
    "黄金ETF": {"mu": 0.07, "sigma": 0.15},
    "货币基金": {"mu": 0.02, "sigma": 0.01},
}


def generate_asset_data(n_days=500):
    """Generate synthetic historical daily returns for asset classes."""
    n_assets = len(ASSET_CLASSES)

    # Create correlated return structure
    mu_vec = np.array([ASSET_PARAMS[a]["mu"] / 252 for a in ASSET_CLASSES])  # Daily mean returns
    sigma_vec = np.array([ASSET_PARAMS[a]["sigma"] / np.sqrt(252) for a in ASSET_CLASSES])

    # Correlation matrix (higher for similar asset types)
    corr = np.eye(n_assets)
    # Stock correlations
    corr[0, 1] = corr[1, 0] = 0.85
    # Bond correlations
    corr[2, 3] = corr[3, 2] = 0.70
    # Gold vs stocks
    corr[0, 4] = corr[4, 0] = 0.15
    corr[1, 4] = corr[4, 1] = 0.10
    # Money market correlations
    corr[5, :] = 0.02
    corr[:, 5] = 0.02
    corr[5, 5] = 1.0
    # Cross correlations
    corr[0, 2] = corr[2, 0] = -0.2  # Stocks vs bonds: negative
    corr[1, 2] = corr[2, 1] = -0.15
    corr[0, 3] = corr[3, 0] = 0.3
    corr[1, 3] = corr[3, 1] = 0.25

    # Ensure positive semidefinite
    eigenvalues = np.linalg.eigvals(corr)
    if np.min(eigenvalues) < 0:
        corr += np.eye(n_assets) * (-np.min(eigenvalues) * 1.01)

    # Generate correlated returns
    cov_matrix = np.diag(sigma_vec) @ corr @ np.diag(sigma_vec)
    returns = np.random.multivariate_normal(mu_vec, cov_matrix, size=n_days)
    returns_df = pd.DataFrame(returns, columns=ASSET_CLASSES)

    print(f"Generated {n_days} days of returns for {n_assets} assets")
    print(f"Annualized returns:")
    for i, a in enumerate(ASSET_CLASSES):
        ann_ret = returns_df[a].mean() * 252
        ann_vol = returns_df[a].std() * np.sqrt(252)
        print(f"  {a}: {ann_ret:.2%} ± {ann_vol:.2%}")

    return returns_df, cov_matrix


def train():
    print("=" * 60)
    print("Training Portfolio Optimization Model")
    print("=" * 60)

    returns_df, cov_matrix = generate_asset_data(500)

    out_dir = os.path.dirname(__file__)
    joblib.dump({
        "returns_df": returns_df,
        "cov_matrix": cov_matrix,
        "asset_classes": ASSET_CLASSES,
        "annual_returns": {a: returns_df[a].mean() * 252 for a in ASSET_CLASSES},
        "annual_vol": {a: returns_df[a].std() * np.sqrt(252) for a in ASSET_CLASSES},
    }, os.path.join(out_dir, "asset_data.joblib"))
    print("Asset data saved.")


def optimize_portfolio(risk_preference="balanced", total_amount=100000):
    """Optimize portfolio allocation using Mean-Variance + Monte Carlo."""
    out_dir = os.path.dirname(__file__)
    data = joblib.load(os.path.join(out_dir, "asset_data.joblib"))
    returns_df = data["returns_df"]
    cov_matrix = data["cov_matrix"]
    assets = data["asset_classes"]
    n_assets = len(assets)

    risk_free_rate = 0.02  # Annual risk-free rate

    # Monte Carlo simulation
    n_portfolios = 10000
    results = np.zeros((4, n_portfolios))
    all_weights = np.zeros((n_portfolios, n_assets))

    annual_returns = returns_df.mean() * 252
    annual_cov = cov_matrix * 252

    for i in range(n_portfolios):
        weights = np.random.random(n_assets)
        weights /= weights.sum()
        all_weights[i] = weights

        port_return = np.sum(annual_returns * weights)
        port_vol = np.sqrt(weights.T @ annual_cov @ weights)
        sharpe = (port_return - risk_free_rate) / port_vol

        results[0, i] = port_return
        results[1, i] = port_vol
        results[2, i] = sharpe
        results[3, i] = port_return / port_vol  # Another ratio

    # Find best portfolio based on risk preference
    risk_params = {
        "conservative": {"max_vol": 0.05, "sharpe_focus": True},
        "balanced": {"max_vol": 0.15, "sharpe_focus": True},
        "aggressive": {"max_vol": 0.30, "sharpe_focus": False},
    }

    rp = risk_params.get(risk_preference, risk_params["balanced"])

    if rp["sharpe_focus"]:
        # Max Sharpe within vol constraint
        valid = results[1] <= rp["max_vol"]
        if valid.sum() == 0:
            valid = np.ones(n_portfolios, dtype=bool)
        best_idx = np.argmax(results[2] * valid)
    else:
        # Max return within vol constraint
        valid = results[1] <= rp["max_vol"]
        if valid.sum() == 0:
            valid = np.ones(n_portfolios, dtype=bool)
        best_idx = np.argmax(results[0] * valid)

    best_weights = all_weights[best_idx]
    best_return = results[0][best_idx]
    best_vol = results[1][best_idx]
    best_sharpe = results[2][best_idx]

    # Calculate max drawdown (simulated)
    n_sim_days = 252
    sim_returns = np.random.multivariate_normal(annual_returns / 252, annual_cov / 252, size=n_sim_days)
    port_returns = sim_returns @ best_weights
    cumulative = np.cumprod(1 + port_returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = abs(np.min(drawdown))

    # Efficient frontier points (for plotting)
    frontier_vols = []
    frontier_returns = []
    target_returns = np.linspace(annual_returns.min(), annual_returns.max(), 20)
    for tr in target_returns:
        try:
            # Minimum variance for target return (simplified)
            valid_idx = np.argsort(np.abs(results[0] - tr))[:100]
            min_vol = results[1][valid_idx].min()
            frontier_vols.append(min_vol)
            frontier_returns.append(tr)
        except Exception:
            continue

    allocation = {assets[i]: round(float(best_weights[i]) * 100, 2) for i in range(n_assets)}

    return {
        "allocation_ratios": allocation,
        "expected_annual_return": round(float(best_return) * 100, 2),
        "expected_annual_volatility": round(float(best_vol) * 100, 2),
        "sharpe_ratio": round(float(best_sharpe), 4),
        "max_drawdown": round(float(max_drawdown) * 100, 2),
        "risk_preference": risk_preference,
        "total_amount": total_amount,
        "rebalance_trigger_threshold": 0.05,  # 5% drift triggers rebalance
        "efficient_frontier": [
            {"volatility": round(float(v) * 100, 2), "return": round(float(r) * 100, 2)}
            for v, r in zip(frontier_vols, frontier_returns)
        ],
    }


if __name__ == "__main__":
    train()

    # Test
    for pref in ["conservative", "balanced", "aggressive"]:
        result = optimize_portfolio(pref, 100000)
        print(f"\n{pref.upper()} Portfolio:")
        for asset, ratio in result["allocation_ratios"].items():
            if ratio > 1:
                print(f"  {asset}: {ratio:.1f}%")
        print(f"  Return: {result['expected_annual_return']}%")
        print(f"  Vol: {result['expected_annual_volatility']}%")
        print(f"  Sharpe: {result['sharpe_ratio']}")
        print(f"  Max DD: {result['max_drawdown']}%")
