import numpy as np
import random
import pandas as pd


def read_multipoles(
    cosmo_idx,
    quintile=0,
    multipole=0,
):
    data = np.load(
        f"../data/full_ap/clustering/ds_cross_xi_smu_zsplit_Rs20_c{cosmo_idx}_ph000.npy",
        allow_pickle=True,
    ).item()
    return np.mean(data["multipoles"], axis=1)[:, quintile, multipole]


def read_params(cosmo_idx):
    params = pd.read_csv(
        f"../data/full_ap/cosmologies/AbacusSummit_c{cosmo_idx}_hod1000.csv"
    )
    return params.to_numpy()


# split train/test/val before adding fisher grid
if __name__ == "__main__":
    quintiles = [0, 1, 3, 4]
    cosmo_idx = list(np.arange(100, 127)) + list(np.arange(130, 181))
    params = []
    for idx in cosmo_idx:
        # multipoles.append(read_multipoles(idx, quintile=quintile))
        params.append(read_params(idx))
    # multipoles = np.array(multipoles)
    params = np.array(params)
    percent_val = 0.1
    percent_test = 0.1
    n_samples = len(params)
    idx = np.arange(n_samples)
    random.shuffle(idx)
    n_val = int(np.floor(percent_val * n_samples))
    n_test = int(np.floor(percent_test * n_samples))
    val_idx = idx[:n_val]
    test_idx = idx[n_val : n_val + n_test]
    train_idx = idx[n_val + n_test :]

    np.save("train_params.npy", params[train_idx].reshape(-1, params.shape[-1]))
    np.save("test_params.npy", params[test_idx].reshape(-1, params.shape[-1]))
    np.save(
        "val_params.npy",
        params[val_idx].reshape(-1, params.shape[-1]),
    )
    for quintile in quintiles:
        for multipole in [0, 1]:
            multipoles = []
            for idx in cosmo_idx:
                multipoles.append(
                    read_multipoles(idx, quintile=quintile, multipole=multipole)
                )
            multipoles = np.array(multipoles)
            np.save(
                f"train_ds{quintile}_m{multipole}.npy",
                multipoles[train_idx].reshape(-1, multipoles.shape[-1]),
            )
            np.save(
                f"test_ds{quintile}_m{multipole}.npy",
                multipoles[test_idx].reshape(-1, multipoles.shape[-1]),
            )
            np.save(
                f"val_ds{quintile}_m{multipole}.npy",
                multipoles[val_idx].reshape(-1, multipoles.shape[-1]),
            )