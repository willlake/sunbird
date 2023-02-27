import numpy as np
from abc import ABC
import pandas as pd
import xarray as xr
from pathlib import Path
from typing import List, Dict, Optional

DATA_PATH = Path(__file__).parent.parent.parent / "data/"


def transform_filters_to_slices(filters: Dict) -> Dict:
    """Transform a dictionary of filters into slices that select from min to max

    Example:
        filters = {'r': (10,100)} , will select the summary statistics for 10 < r < 100

    Args:
        filters (Dict): dictionary of filters.
    Returns:
        Dict: dictionary of filters with slices
    """
    slice_filters = filters.copy()
    for filter, (min, max) in filters.items():
        slice_filters[filter] = slice(min, max)
    return slice_filters


def convert_to_summary(
    data: np.array,
    dimensions: List[str],
    coords: Dict,
    select_filters: Optional[Dict] = None,
    slice_filters: Optional[Dict] = None,
) -> xr.DataArray:
    """Convert numpy array to DataArray summary to filter and select from

    Example:
        slice_filters = {'s': (0, 0.5),}, select_filters = {'multipoles': (0, 2),}
        will return the summary statistics for 0 < s < 0.5 and multipoles 0 and 2

    Args:
        data (np.array): numpy array containing data
        dimensions (List[str]): dimensions names (need to have the same ordering as in data array)
        coords (Dict): coordinates for each dimension
        select_filters (Dict, optional): filters to select values in coordinates. Defaults to None.
        slice_filters (Dict, optional): filters to slice values in coordinates. Defaults to None.

    Returns:
        xr.DataArray: data array summary
    """
    if select_filters:
        select_filters = {k: v for k, v in select_filters.items() if k in dimensions}
    if slice_filters:
        slice_filters = {k: v for k, v in slice_filters.items() if k in dimensions}
    summary = xr.DataArray(
        data,
        dims=dimensions,
        coords=coords,
    )
    if select_filters:
        summary = summary.sel(**select_filters)
    if slice_filters:
        slice_filters = transform_filters_to_slices(slice_filters)
        summary = summary.sel(**slice_filters)
    return summary


class Data(ABC):
    def get_file_path(
        self,
        dataset: str,
        statistic: str,
        suffix: str,
    ) -> Path:
        """Get file path where data is stored

        Args:
            dataset (str): dataset to read
            statistic (str): summary statistic to read
            suffix (str): suffix

        Raises:
            ValueError: if statstics is not known

        Returns:
            Path: path to file
        """
        if statistic == "density_split_auto":
            return (
                self.data_path
                / f"clustering/{dataset}/ds/gaussian/ds_auto_xi_smu_zsplit_Rs10_{suffix}.npy"
            )
        elif statistic == "density_split_cross":
            return (
                self.data_path
                / f"clustering/{dataset}/ds/gaussian/ds_cross_xi_smu_zsplit_Rs10_{suffix}.npy"
            )
        elif statistic == "tpcf":
            return self.data_path / f"clustering/{dataset}/xi_smu/xi_smu_{suffix}.npy"
        raise ValueError(f"Invalid statistic {statistic}")

    def get_observation(
        self, select_from_coords: Optional[Dict] = None, **kwargs
    ) -> np.array:
        """Get observation from data

        Args:
            select_from_coords (Optional[Dict], optional): whether to select values from a specific coordinate.
            Defaults to None.

        Returns:
            np.array: flattened observation
        """
        observation = []
        for statistic in self.statistics:
            observed = self.read_statistic(
                statistic=statistic,
                **kwargs,
            )
            if select_from_coords is not None:
                observed = observed.sel(select_from_coords)
            observation.append(observed.values.reshape(-1))
        return np.hstack(observation)

    def read_statistic(
        self, statistic: str, multiple_realizations: bool = True, **kwargs
    ) -> xr.DataArray:
        """Read summary statistic from data as a DataArray

        Args:
            statistic (str): summary statistic to read
            multiple_realizations (bool, optional):  whether there are multiples realizations stored in
            the same file. Defaults to True.

        Returns:
            xr.DataArray: data array
        """
        if statistic == "tpcf":
            coords = {
                "multipoles": np.arange(3),
            }
            dimensions = ["multipoles", "s"]
        elif "density_split" in statistic:
            coords = {"multipoles": np.arange(3), "quintiles": np.arange(5)}
            dimensions = ["quintiles", "multipoles", "s"]
        path_to_file = self.get_file_path(statistic=statistic, **kwargs)
        data = np.load(
            path_to_file,
            allow_pickle=True,
        ).item()
        s = data["s"]
        data = np.asarray(data["multipoles"])
        if multiple_realizations:
            dimensions.insert(0, "realizations")
            coords["realizations"] = np.arange(data.shape[0])
        coords["s"] = s
        if self.avg_los:
            if multiple_realizations:
                data = np.mean(data, axis=1)
            else:
                data = np.mean(data, axis=0)
        return convert_to_summary(
            data=data,
            dimensions=dimensions,
            coords=coords,
            select_filters=self.select_filters,
            slice_filters=self.slice_filters,
        )


class Abacus(Data):
    def __init__(
        self,
        data_path: Optional[Path] = DATA_PATH,
        dataset: Optional[str] = "different_hods_linsigma",
        statistics: Optional[List[str]] = [
            "density_split_auto",
            "density_split_cross",
            "tpcf",
        ],
        select_filters: Optional[Dict] = {
            "multipoles": [0, 2],
            "quintiles": [0, 1, 3, 4],
        },
        slice_filters: Optional[Dict] = {"s": [0.7, 150.0]},
    ):
        """Abacus data class for the abacus summit latin hypercube of simulations.

        Args:
            data_path (Path, optional): path where data is stored. Defaults to DATA_PATH.
            dataset (str, optional): dataset to read. Defaults to "different_hods_linsigma".
            statistics (List[str], optional): summary statistics to read.
            Defaults to ["density_split_auto", "density_split_cross", "tpcf"].
            select_filters (Dict, optional): filters to select values along coordinates.
            Defaults to {"multipoles": [0, 2], "quintiles": [0, 1, 3, 4]}.
            slice_filters (Dict, optional): filters to slice values along coordinates.
            Defaults to {"s": [0.7, 150.0]}.
        """
        self.data_path = data_path
        self.dataset = dataset
        self.statistics = statistics
        self.select_filters = select_filters
        self.slice_filters = slice_filters
        self.avg_los = True

    def get_file_path(
        self,
        statistic: str,
        cosmology: int,
        phase: int,
    ) -> Path:
        """get file path where data is stored for a given statistic, cosmology, and phase

        Args:
            statistic (str): summary statistic to read
            cosmology (int): cosmology to read within abacus' latin hypercube
            phase (int): phase to read

        Returns:
            Path: path to where data is stored
        """
        return super().get_file_path(
            dataset=self.dataset,
            statistic=statistic,
            suffix=f"c{str(cosmology).zfill(3)}_ph{str(phase).zfill(3)}",
        )

    def get_observation(
        self,
        cosmology: int,
        hod_idx: int,
        phase: int = 0,
    ) -> np.array:
        """get array of a given observation at a cosmology, hod_idx, and phase

        Args:
            cosmology (int): cosmology to read within abacus' latin hypercube
            hod_idx (int): hod_idx to read within a given cosmology
            phase (int): phase to read

        Returns:
            np.array: flattened observation
        """
        return super().get_observation(
            cosmology=cosmology,
            phase=phase,
            select_from_coords={"realizations": hod_idx},
        )

    def get_all_parameters(self, cosmology: int) -> pd.DataFrame:
        """dataframe of parameters used for a given cosmology

        Args:
            cosmology (int): cosmology to read within abacus' latin hypercube

        Returns:
            pd.DataFrame: dataframe of cosmology + HOD parameters
        """
        return pd.read_csv(
            self.data_path
            / f"parameters/{self.dataset}/AbacusSummit_c{str(cosmology).zfill(3)}_hod1000.csv"
        )

    def get_parameters_for_observation(
        self,
        cosmology: int,
        hod_idx: int,
    ) -> Dict:
        """get cosmology + HOD parameters for a particular observation

        Args:
            cosmology (int): cosmology to read within abacus' latin hypercube
            hod_idx (int): hod_idx to read within a given cosmology

        Returns:
            Dict: dictionary of cosmology + HOD parameters
        """
        return self.get_all_parameters(cosmology=cosmology).iloc[hod_idx].to_dict()


class Uchuu(Data):
    def __init__(
        self,
        data_path: Optional[Path] = DATA_PATH,
        statistics: Optional[List[str]] = [
            "density_split_auto",
            "density_split_cross",
            "tpcf",
        ],
        select_filters: Optional[Dict] = {
            "multipoles": [0, 2],
            "quintiles": [0, 1, 3, 4],
        },
        slice_filters: Optional[Dict] = {"s": [0.7, 150.0]},
    ):
        """Uchuu data class to read Uchuu results

        Args:
            data_path (Path, optional): path where data is stored. Defaults to DATA_PATH.
            dataset (str, optional): dataset to read. Defaults to "different_hods_linsigma".
            statistics (List[str], optional): summary statistics to read.
            Defaults to ["density_split_auto", "density_split_cross", "tpcf"].
            select_filters (Dict, optional): filters to select values along coordinates.
            Defaults to {"multipoles": [0, 2], "quintiles": [0, 1, 3, 4]}.
            slice_filters (Dict, optional): filters to slice values along coordinates.
            Defaults to {"s": [0.7, 150.0]}.
        """
        self.data_path = data_path
        self.statistics = statistics
        self.select_filters = select_filters
        self.slice_filters = slice_filters
        self.avg_los = True

    def get_file_path(
        self,
        statistic: str,
        ranking: str,
    ) -> Path:
        """get file path where data is stored for a given statistic, cosmology, and phase

        Args:
            statistic (str): summary statistic to read
            ranking (str): whether to use ranked halos or random halos

        Returns:
            Path: path to where data is stored
        """
        return super().get_file_path(
            dataset="uchuu",
            statistic=statistic,
            suffix=f"{str(ranking)}",
        )

    def get_observation(
        self,
        ranking: str,
    ) -> np.array:
        """get array of a given observation at a cosmology and ranking

        Args:
            ranking (str): whether to use ranked halos or random halos

        Returns:
            np.array: flattened observation
        """
        return super().get_observation(
            ranking=ranking,
            multiple_realizations=False,
        )

    def get_parameters_for_observation(
        self,
    ) -> Dict:
        """get cosmological parameters for a particular observation

        Returns:
            Dict: dictionary of cosmology + HOD parameters
        """
        return {
            "omega_b": 0.02213,
            "omega_cdm": 0.11891,
            "sigma8_m": 0.8288,
            "n_s": 0.9611,
            "nrun": 0.0,
            "N_ur": 2.0328,
            "w0_fld": -1.0,
            "wa_fld": 0.0,
        }


class Patchy(Data):
    def __init__(
        self,
        data_path: Optional[Path] = DATA_PATH,
        statistics: Optional[List[str]] = [
            "density_split_auto",
            "density_split_cross",
            "tpcf",
        ],
        select_filters: Optional[Dict] = {
            "multipoles": [0, 2],
            "quintiles": [0, 1, 3, 4],
        },
        slice_filters: Optional[Dict] = {"s": [0.7, 150.0]},
    ):
        """Patchy data class for the pathcy mocks.

        Args:
            data_path (Path, optional): path where data is stored. Defaults to DATA_PATH.
            statistics (List[str], optional): summary statistics to read.
            Defaults to ["density_split_auto", "density_split_cross", "tpcf"].
            select_filters (Dict, optional): filters to select values along coordinates.
            Defaults to {"multipoles": [0, 2], "quintiles": [0, 1, 3, 4]}.
            slice_filters (Dict, optional): filters to slice values along coordinates.
            Defaults to {"s": [0.7, 150.0]}.
        """
        self.data_path = data_path
        self.statistics = statistics
        self.select_filters = select_filters
        self.slice_filters = slice_filters
        self.avg_los = False

    def get_file_path(
        self,
        statistic: str,
    ):
        """get file path where data is stored for a given statistic

        Args:
            statistic (str): summary statistic to read

        Returns:
            Path: path to where data is stored
        """
        return super().get_file_path(
            dataset="patchy",
            statistic=statistic,
            suffix=f"landyszalay_randomsX50",
        )

    def get_observation(
        self,
        phase: int,
    ) -> np.array:
        """get array of a given observation at a given phase

        Args:
            phase (int): random phase to read

        Returns:
            np.array: flattened observation
        """
        return super().get_observation(
            select_from_coords={"realizations": phase},
            multiple_realizations=True,
        )

    def get_parameters_for_observation(
        self,
    ) -> Dict:
        """get cosmological parameters for a particular observation

        Returns:
            Dict: dictionary of cosmology + HOD parameters
        """
        return {
            "omega_b": 0.02213,
            "omega_cdm": 0.11891,
            "sigma8_m": 0.8288,
            "n_s": 0.9611,
            "nrun": 0.0,
            "N_ur": 2.0328,
            "w0_fld": -1.0,
            "wa_fld": 0.0,
        }


class CMASS(Data):
    def __init__(
        self,
        data_path=DATA_PATH,
        statistics: List[str] = ["density_split_auto", "density_split_cross", "tpcf"],
        select_filters: Dict = {"multipoles": [0, 2], "quintiles": [0, 1, 3, 4]},
        slice_filters: Dict = {"s": [0.7, 150.0]},
    ):
        """CMASS data class to read CMASS data

        Args:
            data_path (Path, optional): path where data is stored. Defaults to DATA_PATH.
            statistics (List[str], optional): summary statistics to read.
            Defaults to ["density_split_auto", "density_split_cross", "tpcf"].
            select_filters (Dict, optional): filters to select values along coordinates.
            Defaults to {"multipoles": [0, 2], "quintiles": [0, 1, 3, 4]}.
            slice_filters (Dict, optional): filters to slice values along coordinates.
            Defaults to {"s": [0.7, 150.0]}.
        """
        self.data_path = data_path
        self.statistics = statistics
        self.select_filters = select_filters
        self.slice_filters = slice_filters
        self.avg_los = True

    def get_file_path(
        self,
        statistic: str,
    ) -> Path:
        """get file path where data is stored for a given statistic, cosmology, and phase

        Args:
            statistic (str): summary statistic to read

        Returns:
            Path: path to where data is stored
        """
        return super().get_file_path(
            dataset="cmasslowz",
            statistic=statistic,
            suffix="cmasslowztot_ngc_landyszalay",
        )

    def get_observation(
        self,
    ) -> np.array:
        """get array of a given observation at a cosmology and ranking

        Returns:
            np.array: flattened observation
        """
        return super().get_observation(
            multiple_realizations=False,
        )

    def get_parameters_for_observation(
        self,
    ) -> Dict:
        """get cosmological parameters for a particular observation

        Returns:
            Dict: dictionary of cosmology + HOD parameters
        """
        return {
            "omega_b": 0.02213,
            "omega_cdm": 0.11891,
            "sigma8_m": 0.8288,
            "n_s": 0.9611,
            "nrun": 0.0,
            "N_ur": 2.0328,
            "w0_fld": -1.0,
            "wa_fld": 0.0,
        }