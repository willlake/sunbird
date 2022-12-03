import numpy as np 
import json
import random


dataset = 'different_hods'

n_derivative_grid = 27
cosmo_idx = list(np.arange(100, 100 + n_derivative_grid)) + list(
    np.arange(130, 181)
)
percent_val = 0.1
percent_test = 0.1
n_samples = len(cosmo_idx)
idx = n_derivative_grid + np.arange(n_samples - n_derivative_grid)
random.shuffle(idx)
n_val = int(np.floor(percent_val * n_samples))
n_test = int(np.floor(percent_test * n_samples))
val_idx = idx[:n_val]
test_idx = idx[n_val : n_val + n_test]
train_idx = list(idx[n_val + n_test :]) + list(range(n_derivative_grid))

split_dict = {
    'train': [int(idx) for idx in train_idx],
    'val': [int(idx) for idx in val_idx],
    'test': [int(idx) for idx in test_idx],
}
with open('../data/train_test_split.json', 'w') as f:
    json.dump(split_dict, f)
