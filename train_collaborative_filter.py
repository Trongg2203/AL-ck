"""
Collaborative Filtering Training Script
========================================
Thuật toán: Simon Funk SVD (Matrix Factorization) — tự implement bằng numpy
Tham khảo:  Simon Funk (2006), "Netflix Update: Try This at Home"
            Y. Koren et al. (2009), "Matrix Factorization Techniques for Recommender Systems"

Không dùng scikit-surprise để tránh vấn đề tương thích NumPy 2.x.
Implement bằng numpy thuần — phù hợp cho báo cáo đồ án tốt nghiệp.

Mô hình:
    r̂(u,i) = μ + b_u + b_i + q_i · p_u
    Trong đó:
        μ   = trung bình rating toàn bộ
        b_u = bias của user u
        b_i = bias của item i
        p_u = vector latent của user u (n_factors chiều)
        q_i = vector latent của item i (n_factors chiều)

Cập nhật (SGD):
    err    = r_ui - r̂(u,i)
    b_u   += lr * (err - reg * b_u)
    b_i   += lr * (err - reg * b_i)
    p_u   += lr * (err * q_i - reg * p_u)
    q_i   += lr * (err * p_u - reg * q_i)

Cách chạy:
    python AI_ck/train_collaborative_filter.py

Yêu cầu:
    pip install pymysql pandas numpy (đã có sẵn, không cần scikit-surprise)
"""

import io
import os
import sys
import pickle
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Fix encoding cho Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── Thư viện ───────────────────────────────────────────────────────
try:
    import pandas as pd
    import numpy as np
    import pymysql
except ImportError as e:
    print(f"[ERROR] Thiếu thư viện: {e}")
    print("Cài đặt: pip install pymysql pandas numpy")
    sys.exit(1)

# ── Cấu hình ───────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent.parent
MODEL_DIR  = ROOT_DIR / "AI_ck" / "models"
MODEL_PATH = MODEL_DIR / "cf_svd_model.pkl"

DB_CONFIG = {
    "host":    "127.0.0.1",
    "port":    3306,
    "user":    "root",
    "password": "",
    "database": "graduation",
    "charset":  "utf8mb4",
}

# SVD Hyperparameters
N_FACTORS  = 50    # số chiều latent space
N_EPOCHS   = 30    # số vòng lặp SGD
LR         = 0.005 # learning rate
REG        = 0.02  # regularization (tránh overfitting)
RANDOM_STATE = 42


# ══════════════════════════════════════════════════════════════════
#  1. ĐỌC DỮ LIỆU
# ══════════════════════════════════════════════════════════════════

def load_ratings_from_db() -> pd.DataFrame:
    """Đọc toàn bộ food_ratings từ MySQL."""
    print("\n[1/5] Đang kết nối cơ sở dữ liệu MySQL...")

    conn = pymysql.connect(**DB_CONFIG)
    try:
        query = """
            SELECT
                r.user_id,
                r.food_id,
                r.rating,
                f.name        AS food_name,
                f.calories,
                f.protein,
                f.carbs,
                f.fat,
                g.goal_type   AS user_goal
            FROM food_ratings r
            JOIN foods          f ON f.id = r.food_id
            JOIN user_goals     g ON g.user_id = r.user_id AND g.status = 0
        """
        df = pd.read_sql(query, conn)
        print(f"      ✓ Đọc được {len(df):,} ratings từ {df['user_id'].nunique()} users, "
              f"{df['food_id'].nunique()} foods")
        return df
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════
#  2. PHÂN TÍCH DỮ LIỆU
# ══════════════════════════════════════════════════════════════════

def analyze_data(df: pd.DataFrame) -> None:
    """Thống kê mô tả dữ liệu ratings."""
    print("\n[2/5] Phân tích dữ liệu:")

    dist = df["rating"].value_counts().sort_index()
    print("      Phân phối rating:")
    for star, count in dist.items():
        bar = "█" * (count // 20)
        print(f"        {star}⭐: {count:>5}  {bar}")

    n_users = df["user_id"].nunique()
    n_foods = df["food_id"].nunique()
    sparsity = 1 - len(df) / (n_users * n_foods)
    print(f"\n      Ma trận: {n_users} users × {n_foods} foods")
    print(f"      Sparsity: {sparsity:.2%}")
    print(f"      Trung bình: {df['rating'].mean():.2f} ± {df['rating'].std():.2f}")

    goal_labels = {0: "Cutting", 1: "Bulking", 2: "Maintaining"}
    goal_dist = df.groupby("user_goal")["user_id"].nunique()
    print("\n      Phân phối users theo goal:")
    for goal_id, count in goal_dist.items():
        print(f"        {goal_labels.get(int(goal_id), '?')}: {count} users")


# ══════════════════════════════════════════════════════════════════
#  3. SIMON FUNK SVD (tự implement)
# ══════════════════════════════════════════════════════════════════

class FunkSVD:
    """
    Simon Funk SVD (Matrix Factorization) cho Collaborative Filtering.

    Mô hình:
        r̂(u,i) = μ + b_u + b_i + q_i · p_u

    Tham số tối ưu bằng Stochastic Gradient Descent (SGD).
    """

    def __init__(
        self,
        n_factors:    int   = 50,
        n_epochs:     int   = 30,
        lr:           float = 0.005,
        reg:          float = 0.02,
        random_state: int   = 42,
    ):
        self.n_factors    = n_factors
        self.n_epochs     = n_epochs
        self.lr           = lr
        self.reg          = reg
        self.random_state = random_state

        # Sẽ được thiết lập trong fit()
        self.mu: float = 0.0
        self.bu: np.ndarray = None  # user biases
        self.bi: np.ndarray = None  # item biases
        self.pu: np.ndarray = None  # user factors
        self.qi: np.ndarray = None  # item factors
        self.user2idx: Dict[str, int] = {}
        self.item2idx: Dict[str, int] = {}
        self.idx2user: Dict[int, str] = {}
        self.idx2item: Dict[int, str] = {}

    def fit(self, df: pd.DataFrame, verbose: bool = True) -> "FunkSVD":
        """
        Train model trên toàn bộ DataFrame có cột [user_id, food_id, rating].
        """
        rng = np.random.default_rng(self.random_state)

        # ── Build index maps ─────────────────────────────────────
        users = df["user_id"].unique().tolist()
        items = df["food_id"].unique().tolist()
        self.user2idx = {u: i for i, u in enumerate(users)}
        self.item2idx = {it: i for i, it in enumerate(items)}
        self.idx2user = {i: u for u, i in self.user2idx.items()}
        self.idx2item = {i: it for it, i in self.item2idx.items()}

        n_users = len(users)
        n_items = len(items)

        # ── Khởi tạo parameters ──────────────────────────────────
        self.mu = float(df["rating"].mean())
        self.bu = np.zeros(n_users)
        self.bi = np.zeros(n_items)
        self.pu = rng.normal(0, 0.1, (n_users, self.n_factors))
        self.qi = rng.normal(0, 0.1, (n_items, self.n_factors))

        # ── Chuẩn bị dữ liệu (arrays cho tốc độ) ─────────────────
        u_arr = np.array([self.user2idx[u] for u in df["user_id"]], dtype=np.int32)
        i_arr = np.array([self.item2idx[it] for it in df["food_id"]], dtype=np.int32)
        r_arr = df["rating"].to_numpy(dtype=np.float64)
        n     = len(r_arr)

        if verbose:
            print(f"      Bắt đầu SGD: {n_users} users × {n_items} items, "
                  f"{self.n_factors} factors, {self.n_epochs} epochs")

        # ── SGD Training ─────────────────────────────────────────
        t0 = time.time()
        for epoch in range(1, self.n_epochs + 1):
            # Shuffle dữ liệu mỗi epoch
            idx = rng.permutation(n)
            u_shuf, i_shuf, r_shuf = u_arr[idx], i_arr[idx], r_arr[idx]

            total_loss = 0.0
            for k in range(n):
                u, i, r = int(u_shuf[k]), int(i_shuf[k]), r_shuf[k]

                # Dự đoán
                r_hat = self.mu + self.bu[u] + self.bi[i] + np.dot(self.qi[i], self.pu[u])
                err   = r - r_hat
                total_loss += err * err

                # Cập nhật biases
                self.bu[u] += self.lr * (err - self.reg * self.bu[u])
                self.bi[i] += self.lr * (err - self.reg * self.bi[i])

                # Cập nhật latent factors
                pu_old      = self.pu[u].copy()
                self.pu[u] += self.lr * (err * self.qi[i] - self.reg * self.pu[u])
                self.qi[i] += self.lr * (err * pu_old     - self.reg * self.qi[i])

            rmse = np.sqrt(total_loss / n)
            if verbose and (epoch % 5 == 0 or epoch == 1):
                elapsed = time.time() - t0
                print(f"        Epoch {epoch:>2}/{self.n_epochs}  "
                      f"RMSE={rmse:.4f}  ({elapsed:.1f}s)")

        if verbose:
            print(f"      ✓ Training hoàn thành! Final RMSE (train): {rmse:.4f}")

        return self

    def predict(self, user_id: str, food_id: str) -> float:
        """Dự đoán rating cho (user_id, food_id)."""
        u = self.user2idx.get(user_id)
        i = self.item2idx.get(food_id)

        if u is None and i is None:
            return self.mu
        if u is None:
            return self.mu + self.bi[i]
        if i is None:
            return self.mu + self.bu[u]

        r_hat = self.mu + self.bu[u] + self.bi[i] + np.dot(self.qi[i], self.pu[u])
        # Clamp về [1, 5]
        return float(np.clip(r_hat, 1.0, 5.0))

    def predict_batch(self, user_id: str, food_ids: List[str]) -> Dict[str, float]:
        """Dự đoán rating cho nhiều foods cùng lúc (nhanh hơn loop)."""
        u = self.user2idx.get(user_id)
        results = {}

        for fid in food_ids:
            i = self.item2idx.get(fid)
            if u is None and i is None:
                results[fid] = self.mu
            elif u is None:
                results[fid] = float(np.clip(self.mu + self.bi[i], 1, 5))
            elif i is None:
                results[fid] = float(np.clip(self.mu + self.bu[u], 1, 5))
            else:
                r = self.mu + self.bu[u] + self.bi[i] + float(self.qi[i] @ self.pu[u])
                results[fid] = float(np.clip(r, 1, 5))

        return results


# ══════════════════════════════════════════════════════════════════
#  4. ĐÁNH GIÁ: K-FOLD CROSS-VALIDATION
# ══════════════════════════════════════════════════════════════════

def cross_validate_svd(
    df: pd.DataFrame,
    n_folds: int = 5,
    n_factors: int = N_FACTORS,
    n_epochs: int = N_EPOCHS,
) -> Tuple[float, float]:
    """
    K-fold cross-validation cho SVD model.
    Trả về (mean_rmse, mean_mae).
    """
    print(f"\n      Chạy {n_folds}-fold cross-validation...")
    rng = np.random.default_rng(RANDOM_STATE)
    df_shuffled = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    n = len(df_shuffled)
    fold_size = n // n_folds

    rmse_list, mae_list = [], []

    for fold in range(n_folds):
        # Tách train/test
        test_start  = fold * fold_size
        test_end    = test_start + fold_size if fold < n_folds - 1 else n
        test_df     = df_shuffled.iloc[test_start:test_end]
        train_df    = pd.concat([
            df_shuffled.iloc[:test_start],
            df_shuffled.iloc[test_end:],
        ])

        # Train
        model = FunkSVD(
            n_factors=n_factors, n_epochs=n_epochs,
            lr=LR, reg=REG, random_state=RANDOM_STATE,
        )
        model.fit(train_df, verbose=False)

        # Đánh giá trên test fold
        errors = []
        for _, row in test_df.iterrows():
            pred = model.predict(row["user_id"], row["food_id"])
            errors.append(row["rating"] - pred)

        errors = np.array(errors)
        rmse_list.append(np.sqrt(np.mean(errors ** 2)))
        mae_list.append(np.mean(np.abs(errors)))
        print(f"        Fold {fold+1}/{n_folds}: RMSE={rmse_list[-1]:.4f}, MAE={mae_list[-1]:.4f}")

    mean_rmse = float(np.mean(rmse_list))
    mean_mae  = float(np.mean(mae_list))
    print(f"      Trung bình: RMSE={mean_rmse:.4f}, MAE={mean_mae:.4f}")
    return mean_rmse, mean_mae


def train_and_evaluate(df: pd.DataFrame):
    """
    Train model đầy đủ với cross-validation + test set evaluation.
    Returns (model, metrics_dict)
    """
    print("\n[3/5] Đang train SVD model...")

    # Cross-validation (5-fold)
    cv_rmse, cv_mae = cross_validate_svd(df)

    # Train/test split 80/20
    print("\n      Đánh giá trên tập test (80/20 split)...")
    test_df  = df.sample(frac=0.2, random_state=RANDOM_STATE)
    train_df = df.drop(test_df.index)

    model_test = FunkSVD(
        n_factors=N_FACTORS, n_epochs=N_EPOCHS,
        lr=LR, reg=REG, random_state=RANDOM_STATE,
    )
    model_test.fit(train_df, verbose=False)

    errors = []
    for _, row in test_df.iterrows():
        pred = model_test.predict(row["user_id"], row["food_id"])
        errors.append(row["rating"] - pred)
    errors = np.array(errors)
    test_rmse = float(np.sqrt(np.mean(errors ** 2)))
    test_mae  = float(np.mean(np.abs(errors)))
    print(f"      RMSE (test): {test_rmse:.4f}")
    print(f"      MAE  (test): {test_mae:.4f}")

    # Train trên toàn bộ data (production model)
    print("\n      Train lại trên toàn bộ dữ liệu (full trainset)...")
    model_full = FunkSVD(
        n_factors=N_FACTORS, n_epochs=N_EPOCHS,
        lr=LR, reg=REG, random_state=RANDOM_STATE,
    )
    model_full.fit(df, verbose=True)

    metrics = {
        "cv_rmse":   cv_rmse,
        "cv_mae":    cv_mae,
        "test_rmse": test_rmse,
        "test_mae":  test_mae,
        "n_users":   int(df["user_id"].nunique()),
        "n_foods":   int(df["food_id"].nunique()),
        "n_ratings": len(df),
        "n_factors": N_FACTORS,
        "n_epochs":  N_EPOCHS,
    }
    return model_full, metrics


# ══════════════════════════════════════════════════════════════════
#  5. LƯU MODEL
# ══════════════════════════════════════════════════════════════════

def save_model(model: FunkSVD, metadata: dict) -> None:
    """Lưu model + metadata vào file .pkl."""
    print(f"\n[4/5] Lưu model...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "model":      model,
        "metadata":   metadata,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "algorithm":  "Simon Funk SVD (custom numpy implementation)",
    }

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)

    size_kb = MODEL_PATH.stat().st_size / 1024
    print(f"      ✓ Đã lưu: {MODEL_PATH}  ({size_kb:.1f} KB)")


# ══════════════════════════════════════════════════════════════════
#  6. DEMO: TOP-N RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════

def demo_recommendations(model: FunkSVD, df: pd.DataFrame, n_recs: int = 10) -> None:
    """In ra top-N gợi ý cho một vài user mẫu."""
    print(f"\n[5/5] Demo top-{n_recs} recommendations:")

    all_food_ids = list(df["food_id"].unique())
    food_names   = df.groupby("food_id")["food_name"].first()
    sample_users = df["user_id"].unique()[:3]

    for user_id in sample_users:
        rated_foods = set(df[df["user_id"] == user_id]["food_id"].tolist())
        unrated     = [fid for fid in all_food_ids if fid not in rated_foods]

        # Dự đoán batch
        scores = model.predict_batch(user_id, unrated)
        top_n  = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n_recs]

        user_goal  = df[df["user_id"] == user_id]["user_goal"].iloc[0]
        goal_label = {0: "Cutting", 1: "Bulking", 2: "Maintaining"}.get(int(user_goal), "?")
        print(f"\n      User {user_id} (Goal: {goal_label}) — {len(rated_foods)} ratings đã có")
        for i, (fid, score) in enumerate(top_n, 1):
            food_name = food_names.get(fid, fid)
            print(f"        {i:>2}. [{score:.2f}⭐] {food_name}")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  COLLABORATIVE FILTERING TRAINING")
    print("  Thuật toán: Simon Funk SVD (pure numpy)")
    print("  Dự án: Food AI For Gym Members")
    print("=" * 60)

    df = load_ratings_from_db()
    analyze_data(df)
    model, metrics = train_and_evaluate(df)
    save_model(model, metrics)
    demo_recommendations(model, df)

    print("\n" + "=" * 60)
    print("  KẾT QUẢ TRAINING:")
    print(f"  RMSE (5-fold CV): {metrics['cv_rmse']:.4f}")
    print(f"  MAE  (5-fold CV): {metrics['cv_mae']:.4f}")
    print(f"  RMSE (test set) : {metrics['test_rmse']:.4f}")
    print(f"  Model saved tại : {MODEL_PATH}")
    print("=" * 60)
    print("\n✓ Training hoàn thành! Model sẵn sàng cho API.")


if __name__ == "__main__":
    main()

