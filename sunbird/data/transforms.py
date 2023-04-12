from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import xarray as xr
import numpy as np
import sys
import pickle


class BaseTransform(ABC):
    @abstractmethod
    def transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Transform a summary

        Args:
            summary (xr.DataArray): summary to transform

        Returns:
            xr.DataArray: transformed summary
        """
        return

    @abstractmethod
    def inverse_transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Inverse the transform

        Args:
            summary (xr.DataArray): transformed summary

        Returns:
            xr.DataArray: original summary
        """
        return

    def get_parameter_dict(self,)->Dict:
        """ get parameters needed for transform

        Returns:
            Dict: dictionary of parameteres 
        """
        return self.__dict__

    def fit_transform(self, summary: xr.DataArray,)->xr.DataArray:
        """Fit the transform from data in summary and transform summary.


        Args:
            summary (xr.DataArray): data to fit and transform 
            dimensions (xr.DataArray): dimensions over which to fit 

        Returns:
            xr.DataArray: transformed summary 
        """
        self.fit(summary,)
        return self.transform(summary)


class Transforms:
    def __init__(self, transforms: List[BaseTransform]):
        """ Combine multiple transforms into one

        Args:
            transforms (List[BaseTransform]): list of transforms to combine 
        """
        self.transforms = transforms

    @classmethod
    def from_file(cls, filename: str)->'Transforms':
        """ Load transforms from file

        Args:
            filename (str): file to load 

        Returns:
            Transforms: Transforms object 
        """
        with open(filename, 'rb') as f:
            param_dict = pickle.load(f)
        transforms = []
        for key, value in param_dict.items():
            transforms.append(
                getattr(sys.modules[__name__], key)(**value)
            )
        return cls(
            transforms=transforms,
        )

    def fit_transform(self, summary, path_to_store=None,):
        """Fit the transform from data in summary and transform summary.


        Args:
            summary (xr.DataArray): data to fit and transform 
            path_to_store (str, optional): path to store parameters. Defaults to None.

        Returns:
            xr.DataArray: transformed summary 
        """
        for transform in self.transforms:
            if hasattr(transform, 'fit'):
                summary = transform.fit_transform(summary,)
            else:
                summary = transform.transform(summary)
        if path_to_store is not None:
            self.store_transform_params(path_to_store=path_to_store)
        return summary 

    def store_transform_params(self, path_to_store: str):
        """
        Store the parameters of the transforms

        Args:
            path_to_store (str): path to store parameters
        """
        param_dict = {}
        for transform in self.transforms:
            if hasattr(transform, 'fit'):
                param_dict[transform.__class__.__name__] = transform.get_parameter_dict()
            else:
                param_dict[transform.__class__.__name__] = {} 
        with open(path_to_store, 'wb') as f:
            pickle.dump(param_dict, f)

    def transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Transform a summary

        Args:
            summary (xr.DataArray): summary to transform

        Returns:
            xr.DataArray: transformed summary
        """
        summary = summary.copy()
        for transform in self.transforms:
            summary = transform.transform(summary)
        return summary

    def inverse_transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Inverse the transform

        Args:
            summary (xr.DataArray): transformed summary

        Returns:
            xr.DataArray: original summary
        """
        for transform in self.transforms[::-1]:
            summary = transform.inverse_transform(summary)
        return summary

class Normalize(BaseTransform):
    def __init__(
        self,
        training_min = None,
        training_max = None,
        dimensions: Optional[List[str]] = None,
        **kwargs,
    ):
        """Normalize the summary statistics

        Args:
            training_min (float, optional): minimum value for training. Defaults to None.
            training_max (float, optional): maximum value for training. Defaults to None.
            dimensions (List[str], optional): dimensions over which to normalize. Defaults to None.
        """
        self.training_min = training_min
        self.training_max = training_max
        self.dimensions = dimensions

    def fit(self, summary: xr.DataArray,):
        if self.dimensions is not None:
            self.training_min = summary.min(dim=self.dimensions)
            self.training_max = summary.max(dim=self.dimensions)
        else:
            self.training_min = summary.min()
            self.training_max = summary.max()

    def transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Transform a summary

        Args:
            summary (xr.DataArray): summary to transform

        Returns:
            xr.DataArray: transformed summary
        """
        return (summary - self.training_min) / (self.training_max - self.training_min)

    def inverse_transform(self, summary: xr.DataArray) -> xr.DataArray:
        return summary * (self.training_max - self.training_min) + self.training_min

class Standarize(BaseTransform):
    def __init__(
        self,
        training_mean = None,
        training_std = None,
        dimensions: Optional[List[str]] = None,
        **kwargs,
    ):
        """Normalize the summary statistics

        Args:
            training_min (float, optional): minimum value for training. Defaults to None.
            training_max (float, optional): maximum value for training. Defaults to None.
        """
        self.training_mean = training_mean
        self.training_std = training_std
        self.dimensions = dimensions

    def fit(self, training_summary,):
        if self.dimensions is not None:
            self.training_mean = training_summary.mean(dim=self.dimensions)
            self.training_std = training_summary.std(dim=self.dimensions)
        else:
            self.training_mean = training_summary.mean()
            self.training_std = training_summary.std()

    def transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Transform a summary

        Args:
            summary (xr.DataArray): summary to transform

        Returns:
            xr.DataArray: transformed summary
        """
        return (summary - self.training_mean) / self.training_std

    def inverse_transform(self, summary: xr.DataArray) -> xr.DataArray:
        return summary * self.training_std + self.training_mean
    

class LogSqrt(BaseTransform):
    def __init__(
        self,
        min_monopole: float = 0.011,
        min_quadrupole: float = -30.0,
        **kwargs,
    ):
        """Transform the monopole and quadrupole to log and sqrt, respectively

        Args:
            min_monopole (float, optional): minimum monopole value. Defaults to 0.011.
            min_quadrupole (float, optional): minimum quadrupole value. Defaults to -30..
        """
        self.min_monopole = min_monopole
        self.min_quadrupole = min_quadrupole

    def transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Transform a summary

        Args:
            summary (xr.DataArray): summary to transform

        Returns:
            xr.DataArray: transformed summary
        """
        summary.loc[{"multipoles": 0}] = np.log10(
            summary.sel(multipoles=0) - self.min_monopole
        )
        summary.loc[{"multipoles": 1}] = (
            summary.sel(multipoles=1) - self.min_quadrupole
        ) ** 0.5
        return summary

    def inverse_transform(self, summary: xr.DataArray) -> xr.DataArray:
        """Inverse the transform

        Args:
            summary (xr.DataArray): transformed summary

        Returns:
            xr.DataArray: original summary
        """
        summary.loc[{"multipoles": 0}] = 10 ** (
            summary.sel(multipoles=0) + self.min_monopole
        )
        summary.loc[{"multipoles": 1}] = (
            summary.sel(multipoles=1) + self.min_quadrupole
        ) ** 2
        return summary