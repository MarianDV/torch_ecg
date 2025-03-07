# -*- coding: utf-8 -*-
"""
Base classes for datasets from different sources:

    - PhysioNet
    - NSRR
    - CPSC
    - Other databases

Remarks
-------
1. For whole-dataset visualizing: http://zzz.bwh.harvard.edu/luna/vignettes/dataplots/
2. Visualizing using UMAP: http://zzz.bwh.harvard.edu/luna/vignettes/nsrr-umap/

"""

import logging
import os
import posixpath
import pprint
import re
import textwrap
import time
import warnings
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from string import punctuation
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import requests
import scipy.signal as SS
import wfdb
from pyedflib import EdfReader

from ..cfg import _DATA_CACHE, CFG, DEFAULTS
from ..utils import ecg_arrhythmia_knowledge as EAK  # noqa : F401
from ..utils.download import http_get
from ..utils.misc import CitationMixin, ReprMixin, dict_to_str, get_record_list_recursive, init_logger
from .aux_data import get_physionet_dbs

__all__ = [
    "WFDB_Beat_Annotations",
    "WFDB_Non_Beat_Annotations",
    "WFDB_Rhythm_Annotations",
    "PhysioNetDataBase",
    "NSRRDataBase",
    "CPSCDataBase",
    "DEFAULT_FIG_SIZE_PER_SEC",
    "BeatAnn",
    "DataBaseInfo",
    "PSGDataBaseMixin",
]


WFDB_Beat_Annotations = {
    "N": "Normal beat",
    "L": "Left bundle branch block beat",
    "R": "Right bundle branch block beat",
    "B": "Bundle branch block beat (unspecified)",
    "A": "Atrial premature beat",
    "a": "Aberrated atrial premature beat",
    "J": "Nodal (junctional) premature beat",
    "S": "Supraventricular premature or ectopic beat (atrial or nodal)",
    "V": "Premature ventricular contraction",
    "r": "R-on-T premature ventricular contraction",
    "F": "Fusion of ventricular and normal beat",
    "e": "Atrial escape beat",
    "j": "Nodal (junctional) escape beat",
    "n": "Supraventricular escape beat (atrial or nodal)",
    "E": "Ventricular escape beat",
    "/": "Paced beat",
    "f": "Fusion of paced and normal beat",
    "Q": "Unclassifiable beat",
    "?": "Beat not classified during learning",
}

WFDB_Non_Beat_Annotations = {
    "[": "Start of ventricular flutter/fibrillation",
    "!": "Ventricular flutter wave",
    "]": "End of ventricular flutter/fibrillation",
    "x": "Non-conducted P-wave (blocked APC)",
    "(": "Waveform onset",
    ")": "Waveform end",
    "p": "Peak of P-wave",
    "t": "Peak of T-wave",
    "u": "Peak of U-wave",
    "`": "PQ junction",
    "'": "J-point",
    "^": "(Non-captured) pacemaker artifact",
    "|": "Isolated QRS-like artifact",
    "~": "Change in signal quality",
    "+": "Rhythm change",
    "s": "ST segment change",
    "T": "T-wave change",
    "*": "Systole",
    "D": "Diastole",
    "=": "Measurement annotation",
    '"': "Comment annotation",
    "@": "Link to external data",
}

WFDB_Rhythm_Annotations = {
    "(AB": "Atrial bigeminy",
    "(AFIB": "Atrial fibrillation",
    "(AFL": "Atrial flutter",
    "(B": "Ventricular bigeminy",
    "(BII": "2° heart block",
    "(IVR": "Idioventricular rhythm",
    "(N": "Normal sinus rhythm",
    "(NOD": "Nodal (A-V junctional) rhythm",
    "(P": "Paced rhythm",
    "(PREX": "Pre-excitation (WPW)",
    "(SBR": "Sinus bradycardia",
    "(SVTA": "Supraventricular tachyarrhythmia",
    "(T": "Ventricular trigeminy",
    "(VFL": "Ventricular flutter",
    "(VT": "Ventricular tachycardia",
}


class _DataBase(ReprMixin, ABC):
    """Universal abstract base class for all databases.

    Parameters
    ----------
    db_dir : str or pathlib.Path, optional
        Storage path of the database.
        If not specified, data will be fetched from Physionet.
    working_dir : str, optional
        Working directory, to store intermediate files and log files.
    verbose : int, default 1
        Level of logging verbosity.
    kwargs : dict, optional
        Auxilliary key word arguments

    """

    def __init__(
        self,
        db_name: str,
        db_dir: Optional[Union[str, Path]] = None,
        working_dir: Optional[Union[str, Path]] = None,
        verbose: int = 1,
        **kwargs: Any,
    ) -> None:
        self.db_name = db_name
        if db_dir is None:
            db_dir = _DATA_CACHE / db_name
            warnings.warn(
                f"`db_dir` is not specified, " f"using default `{db_dir}` as the storage path",
                RuntimeWarning,
            )
        self.db_dir = Path(db_dir).expanduser().resolve().absolute()
        if not self.db_dir.exists():
            self.db_dir.mkdir(parents=True, exist_ok=True)
            warnings.warn(
                f"`{self.db_dir}` does not exist. It is now created. "
                "Please check if it is set correctly. "
                "Or if you may want to download the database into this folder, "
                "please use the `download()` method.",
                RuntimeWarning,
            )
        self.working_dir = Path(working_dir or DEFAULTS.working_dir).expanduser().resolve().absolute() / self.db_name
        self.working_dir.mkdir(parents=True, exist_ok=True)

        self.logger = kwargs.get("logger", None)
        if self.logger is None:
            self.logger = init_logger(
                log_dir=False,
                suffix=self.__class__.__name__,
                verbose=verbose,
            )
        else:
            assert isinstance(self.logger, logging.Logger), "logger must be a `logging.Logger` instance"

        self.data_ext = None
        self.ann_ext = None
        self.header_ext = "hea"
        self.verbose = verbose
        self._df_records = pd.DataFrame()
        self._all_records = None

        self._subsample = kwargs.get("subsample", None)
        assert (
            self._subsample is None or 0 < self._subsample <= 1
        ), f"`subsample` must be in (0, 1], but got `{self._subsample}`"

    @abstractmethod
    def _ls_rec(self) -> None:
        """Find all records in the database."""
        raise NotImplementedError

    @abstractmethod
    def load_data(self, rec: Union[str, int], **kwargs) -> Any:
        """Load data from the record."""
        raise NotImplementedError

    @abstractmethod
    def load_ann(self, rec: Union[str, int], **kwargs) -> Any:
        """Load annotations of the record.

        NOTE that the records might have several annotation files.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def database_info(self) -> "DataBaseInfo":
        """The :class:`DataBaseInfo` object of the database."""
        raise NotImplementedError

    def get_citation(self, format: Optional[str] = None, style: Optional[str] = None) -> None:
        """Get the citations of the papers related to the database.

        Parameters
        ----------
        lookup : bool, default True
            Whether to lookup the citation from the DOI or not.
        format : str, optional
            Format of the final output
            If specified, the default format ("bib") will be overrided.
        style : str, optional
            Style of the final output.
            If specified, the default style ("apa") will be overrided.
            Valid only when `format` is ``"text"``.
        print_result : bool, default False
            Whether to print the final output
            instead of returning it or not.

        Returns
        -------
        None

        """
        self.database_info.get_citation(lookup=True, format=format, style=style, timeout=10.0, print_result=True)

    def _auto_infer_units(self, sig: np.ndarray, sig_type: str = "ECG") -> str:
        """Automatically infer the units of the signal.

        It is assumed that `sig` is not raw signal, but with baseline removed.

        Parameters
        ----------
        sig : ndarray
            The signal to infer its units.
        sig_type : str, default "ECG"
            Type of the signal, case insensitive.

        Returns
        -------
        units : {"μV", "mV"}
            Units of the signal.

        """
        if sig_type.lower() == "ecg":
            _MAX_mV = 20  # 20mV, seldom an ECG device has range larger than this value
            max_val = np.max(np.abs(sig))
            if max_val > _MAX_mV:
                units = "μV"
            else:
                units = "mV"
        else:
            raise NotImplementedError(f"not implemented for {sig_type}")
        return units

    @property
    def all_records(self) -> List[str]:
        if self._all_records is None:
            self._ls_rec()
        return self._all_records

    def get_absolute_path(self, rec: Union[str, int], extension: Optional[str] = None) -> Path:
        """Get the absolute path of the record.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.
        extension : str, optional
            Extension of the file.

        Returns
        -------
        path : pathlib.Path
            Absolute path of the file.

        """
        if isinstance(rec, int):
            rec = self[rec]
        path = self._df_records.loc[rec].path
        if extension is not None:
            path = path.with_suffix(extension if extension.startswith(".") else f".{extension}")
        return path

    def _normalize_leads(
        self,
        leads: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        all_leads: Optional[Sequence[str]] = None,
        numeric: bool = False,
    ) -> List[Union[str, int]]:
        """Normalize the leads to a list of standard lead names.

        Parameters
        ----------
        leads : str or int or List[str] or List[int], optional
            the (names of) leads to normalize
        all_leads : list of str, optional
            All leads of the records in the database,
            If is None, the database class should have attribute `all_leads`,
            and `self.all_leads` will be used.
        numeric : bool, default False
            If True, indices of the leads will be returned
            instead of lead names.

        Returns
        -------
        leads : List[str] or List[int]
            The normalized leads

        """
        if all_leads is None:
            assert hasattr(
                self, "all_leads"
            ), "If `all_leads` is not specified, the database class should have attribute `all_leads`!"
            all_leads = self.all_leads
        err_msg = (
            f"`leads` should be a subset of {all_leads} or non-negative integers "
            f"less than {len(all_leads)}, but got {leads}"
        )
        if leads is None or (isinstance(leads, str) and leads.lower() == "all"):
            _leads = all_leads
        elif isinstance(leads, str):
            _leads = [leads]
        elif isinstance(leads, int):
            assert len(all_leads) > leads >= 0, err_msg
            _leads = [all_leads[leads]]
        else:
            try:
                _leads = [ld if isinstance(ld, str) else all_leads[ld] for ld in leads]
            except Exception:
                raise AssertionError(err_msg)
        assert set(_leads).issubset(all_leads), err_msg
        if numeric:
            _leads = [all_leads.index(ld) for ld in _leads]
        return _leads

    @classmethod
    def get_arrhythmia_knowledge(cls, arrhythmias: Union[str, List[str]]) -> None:
        """Knowledge about ECG features of specific arrhythmias.

        Parameters
        ----------
        arrhythmias : str or List[str]
            The arrhythmia(s) to check,
            in abbreviations or in SNOMEDCTCode.

        Returns
        -------
        None

        """
        if isinstance(arrhythmias, str):
            d = [arrhythmias]
        else:
            d = arrhythmias
        for idx, item in enumerate(d):
            print(dict_to_str(eval(f"EAK.{item}")))
            if idx < len(d) - 1:
                print("*" * 110)

    def extra_repr_keys(self) -> List[str]:
        return [
            "db_name",
            "db_dir",
        ]

    @property
    @abstractmethod
    def url(self) -> Union[str, List[str]]:
        """URL(s) for downloading the database."""
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.all_records)

    def __getitem__(self, index: int) -> str:
        return self.all_records[index]


class PhysioNetDataBase(_DataBase):
    """Base class for readers for PhysioNet database.

    PhysioNet is a large repository of freely available biomedical signals,
    including ECG, EEG, EMG, and other signals.
    The website is [#phy_website]_.

    Parameters
    ----------
    db_name : str
        Name of the database.
    db_dir : str or pathlib.Path, optional
        Storage path of the database.
        If is None, `wfdb` will fetch data from PhysioNet.
    working_dir : str or pathlib.Path, optional
        Working directory, to store intermediate files and log files.
    verbose : int, default 1
        Verbosity level for logging.
    kwargs : dict, optional
        Auxilliary key word arguments.

    References
    ----------
    .. [#phy_website] https://www.physionet.org/

    """

    def __init__(
        self,
        db_name: str,
        db_dir: Optional[Union[str, Path]] = None,
        working_dir: Optional[Union[str, Path]] = None,
        verbose: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_name=db_name,
            db_dir=db_dir,
            working_dir=working_dir,
            verbose=verbose,
            **kwargs,
        )
        # `self.fs` for those with single signal source, e.g. ECG,
        # for those with multiple signal sources like PSG,
        # `self.fs` is default to the frequency of ECG if ECG applicable
        self.fs = kwargs.get("fs", None)
        self._all_records = None
        self._version = None
        self._url_compressed = None

        self.df_all_db_info = get_physionet_dbs()

        if self.verbose > 2:
            self.df_all_db_info = (
                pd.DataFrame(
                    wfdb.get_dbs(),
                    columns=[
                        "db_name",
                        "db_description",
                    ],
                )
                .drop_duplicates()
                .reset_index(drop=True)
            )

    def _ls_rec(self, db_name: Optional[str] = None, local: bool = True) -> None:
        """
        Find all records (relative path without file extension),
        and save into some private attributes for further use.

        Parameters
        ----------
        db_name : str, optional
            Name of the database for using :meth:`wfdb.get_record_list`.
            If is None, :attr:`self.db_name` will be used.
        local : bool, default True
            If True, search records in local storage,
            prior using :meth:`wfdb.get_record_list`.

        Returns
        -------
        None

        """
        empty_warning_msg = (
            "No records found in the database! "
            "Please check if path to the database is correct. "
            "Or you can try to download the database first using the `download` method."
        )
        if local:
            self._ls_rec_local()
            if len(self._df_records) == 0:
                warnings.warn(empty_warning_msg, RuntimeWarning)
            return
        try:
            self._df_records = pd.DataFrame()
            self._df_records["record"] = wfdb.get_record_list(db_name or self.db_name)
            self._df_records["path"] = self._df_records["record"].apply(lambda x: (self.db_dir / x).resolve())
            # keep only the records that exist in `self.db_dir`
            # NOTE
            # 1. data files might be in some subdirectories of `self.db_dir`
            # 2. `wfdb.get_record_list` will return records without file extension
            self._df_records = self._df_records[self._df_records["path"].apply(lambda x: len(x.parent.glob(f"{x.name}.*")) > 0)]
            # if no record found,
            # search locally and recursively inside `self.db_dir`
            if len(self._df_records) == 0:
                return self._ls_rec_local()
            self._df_records["record"] = self._df_records["path"].apply(
                lambda x: x.name
            )  # remove relative path, leaving only the record name
            self._df_records.set_index("record", inplace=True)
            if self._subsample is not None:
                size = min(
                    len(self._df_records),
                    max(1, int(round(self._subsample * len(self._df_records)))),
                )
                self.logger.debug(f"subsample `{size}` records from `{len(self._df_records)}`")
                self._df_records = self._df_records.sample(n=size, random_state=DEFAULTS.SEED, replace=False)
            self._all_records = self._df_records.index.tolist()
        except Exception:
            self._ls_rec_local()
        if len(self._df_records) == 0:
            warnings.warn(empty_warning_msg, RuntimeWarning)

    def _ls_rec_local(self) -> None:
        """Find all records in :attr:`self.db_dir`."""
        record_list_fp = self.db_dir / "RECORDS"
        self._df_records = pd.DataFrame()
        if record_list_fp.is_file():
            self._df_records["record"] = [item for item in record_list_fp.read_text().splitlines() if len(item) > 0]
            if len(self._df_records) > 0:
                if self._subsample is not None:
                    size = min(
                        len(self._df_records),
                        max(1, int(round(self._subsample * len(self._df_records)))),
                    )
                    self.logger.debug(f"subsample `{size}` records from `{len(self._df_records)}`")
                    self._df_records = self._df_records.sample(n=size, random_state=DEFAULTS.SEED, replace=False)
                self._df_records["path"] = self._df_records["record"].apply(lambda x: (self.db_dir / x).resolve())
                self._df_records = self._df_records[self._df_records["path"].apply(lambda x: x.is_file())]
                self._df_records["record"] = self._df_records["path"].apply(lambda x: x.name)

        if len(self._df_records) == 0:
            print("Please wait patiently to let the reader find " "all records of the database from local storage...")
            start = time.time()
            self._df_records["path"] = get_record_list_recursive(self.db_dir, self.data_ext, relative=False)
            if self._subsample is not None:
                size = min(
                    len(self._df_records),
                    max(1, int(round(self._subsample * len(self._df_records)))),
                )
                self.logger.debug(f"subsample `{size}` records from `{len(self._df_records)}`")
                self._df_records = self._df_records.sample(n=size, random_state=DEFAULTS.SEED, replace=False)
            self._df_records["path"] = self._df_records["path"].apply(lambda x: Path(x))
            self.logger.info(f"Done in {time.time() - start:.3f} seconds!")
            self._df_records["record"] = self._df_records["path"].apply(lambda x: x.name)
        self._df_records.set_index("record", inplace=True)
        self._all_records = self._df_records.index.values.tolist()

    def get_subject_id(self, rec: Union[str, int]) -> int:
        """Attach a unique subject ID for the record.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.

        Returns
        -------
        int
            Subject ID associated with the record.

        """
        raise NotImplementedError

    def load_data(
        self,
        rec: Union[str, int],
        leads: Optional[Union[str, int, Sequence[Union[str, int]]]] = None,
        sampfrom: Optional[int] = None,
        sampto: Optional[int] = None,
        data_format: str = "channel_first",
        units: Union[str, type(None)] = "mV",
        fs: Optional[Real] = None,
        return_fs: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, Real]]:
        """Load physical (converted from digital) ECG data,
        which is more understandable for humans;
        or load digital signal directly.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.
        leads : str or int or Sequence[str] or Sequence[int], optional
            The leads of the ECG data to load.
            None or "all" for all leads.
        sampfrom : int, optional
            Start index of the data to be loaded.
        sampto : int, optional
            End index of the data to be loaded.
        data_format : str, default "channel_first"
            Format of the ECG data,
            "channel_last" (alias "lead_last"), or
            "channel_first" (alias "lead_first"), or
            "flat" (alias "plain") which is valid only when `leads` is a single lead
        units : str or None, default "mV"
            Units of the output signal, can also be "μV" (aliases "uV", "muV").
            None for digital data, without digital-to-physical conversion.
        fs : numbers.Real, optional
            Sampling frequency of the output signal.
            If not None, the loaded data will be resampled to this frequency;
            if None, `self.fs` will be used if available and not None;
            otherwise, the original sampling frequency will be used.
        return_fs : bool, default False
            Whether to return the sampling frequency of the output signal.

        Returns
        -------
        data : numpy.ndarray
            The ECG data loaded from the record,
            with given `units` and `data_format`.
        data_fs : numbers.Real, optional
            Sampling frequency of the output signal.
            Returned if `return_fs` is True.

        """
        fp = str(self.get_absolute_path(rec))

        if hasattr(self, "all_leads"):
            all_leads = self.all_leads
        else:
            all_leads = wfdb.rdheader(fp).sig_name
        _leads = self._normalize_leads(leads, all_leads, numeric=False)

        allowed_data_format = [
            "channel_first",
            "lead_first",
            "channel_last",
            "lead_last",
            "flat",
            "plain",
        ]
        assert (
            data_format.lower() in allowed_data_format
        ), f"`data_format` should be one of `{allowed_data_format}`, but got `{data_format}`"
        if len(_leads) > 1:
            assert data_format.lower() in ["channel_first", "lead_first", "channel_last", "lead_last",], (
                "`data_format` should be one of `['channel_first', 'lead_first', 'channel_last', 'lead_last']` "
                f"when the passed number of `leads` is larger than 1, but got `{data_format}`"
            )

        allowed_units = ["mv", "uv", "μv", "muv"]
        assert (
            units is None or units.lower() in allowed_units
        ), f"`units` should be one of `{allowed_units}` or None, but got `{units}`"

        rdrecord_kwargs = dict(
            sampfrom=sampfrom or 0,
            sampto=sampto,
            physical=units is not None,
            return_res=DEFAULTS.DTYPE.INT,
            channels=[all_leads.index(ld) for ld in _leads],
        )  # use `channels` instead of `channel_names` since there're exceptional cases where `channel_names` has duplicates
        wfdb_rec = wfdb.rdrecord(fp, **rdrecord_kwargs)

        # p_signal or d_signal is in the format of "lead_last", and with units in "mV"
        if units is None:
            data = wfdb_rec.d_signal
        elif units.lower() == "mv":
            data = wfdb_rec.p_signal
        elif units.lower() in ["μv", "uv", "muv"]:
            data = 1000 * wfdb_rec.p_signal

        if fs is not None:
            data_fs = fs
        elif hasattr(self, "fs"):
            data_fs = self.fs
        else:
            data_fs = wfdb_rec.fs
        if data_fs != wfdb_rec.fs:
            data = SS.resample_poly(data, data_fs, wfdb_rec.fs, axis=0).astype(data.dtype)

        if data_format.lower() in ["channel_first", "lead_first"]:
            data = data.T
        elif data_format.lower() in ["flat", "plain"]:
            data = data.flatten()

        if return_fs:
            return data, data_fs
        return data

    def helper(self, items: Union[List[str], str, type(None)] = None) -> None:
        """Print corr. meanings of symbols belonging to `items`.

        More details can be found
        in the PhysioNet WFDB annotation manual [#ann_man]_.

        Parameters
        ----------
        items : str or List[str], optional
            Items to print.
            If is None, then a comprehensive printing
            of meanings of all symbols will be performed.

        Returns
        -------
        None

        References
        ----------
        .. [#ann_man] https://archive.physionet.org/physiobank/annotations.shtml

        """
        attrs = vars(self)
        methods = [
            func for func in dir(self) if callable(getattr(self, func)) and not (func.startswith("__") and func.endswith("__"))
        ]

        beat_annotations = deepcopy(WFDB_Beat_Annotations)
        non_beat_annotations = deepcopy(WFDB_Non_Beat_Annotations)
        rhythm_annotations = deepcopy(WFDB_Rhythm_Annotations)

        all_annotations = [
            beat_annotations,
            non_beat_annotations,
            rhythm_annotations,
        ]

        summary_items = [
            "beat",
            "non-beat",
            "rhythm",
        ]

        if items is None:
            _items = [
                "attributes",
                "methods",
                "beat",
                "non-beat",
                "rhythm",
            ]
        elif isinstance(items, str):
            _items = [items]
        else:
            _items = items

        pp = pprint.PrettyPrinter(indent=4)

        if "attributes" in _items:
            print("--- helpler - attributes ---")
            pp.pprint(attrs)
        if "methods" in _items:
            print("--- helpler - methods ---")
            pp.pprint(methods)
        if "beat" in _items:
            print("--- helpler - beat ---")
            pp.pprint(beat_annotations)
        if "non-beat" in _items:
            print("--- helpler - non-beat ---")
            pp.pprint(non_beat_annotations)
        if "rhythm" in _items:
            print("--- helpler - rhythm ---")
            pp.pprint(rhythm_annotations)

        for k in _items:
            if k in summary_items:
                continue
            for a in all_annotations:
                if k in a.keys() or "(" + k in a.keys():
                    try:
                        print(f"`{k.split('(')[1]}` stands for `{a[k]}`")
                    except IndexError:
                        try:
                            print(f"`{k}` stands for `{a[k]}`")
                        except KeyError:
                            print(f"`{k}` stands for `{a['('+k]}`")

    def get_file_download_url(self, file_name: Union[str, Path]) -> str:
        """Get the download url of the file.

        Parameters
        ----------
        file_name : str or pathlib.Path
            Name of the file,
            e.g. "data/001a.dat", "training/tr03-0005/tr03-0005.mat", etc.

        Returns
        -------
        url : str
            URL of the file to be downloaded.

        """
        url = posixpath.join(
            wfdb.io.download.PN_INDEX_URL,
            self.db_name,
            self.version,
            file_name,
        )
        return url

    @property
    def version(self) -> str:
        """Version of the database."""
        if self._version is not None:
            return self._version
        try:
            self._version = wfdb.io.record.get_version(self.db_name)
        except Exception:
            warnings.warn(
                "Cannot get the version number from PhysioNet! Defaults to '1.0.0'",
                RuntimeWarning,
            )
            self._version = "1.0.0"
        return self._version

    @property
    def webpage(self) -> str:
        """URL of the database webpage"""
        return posixpath.join(wfdb.io.download.PN_CONTENT_URL, f"{self.db_name}/{self.version}")

    @property
    def url(self) -> str:
        """URL of the database index page for downloading."""
        return posixpath.join(wfdb.io.download.PN_INDEX_URL, f"{self.db_name}/{self.version}")

    @property
    def url_(self) -> Union[str, type(None)]:
        """URL of the compressed database file for downloading."""
        if self._url_compressed is not None:
            return self._url_compressed
        domain = "https://physionet.org/static/published-projects/"
        punct = re.sub("[\\-:]", "", punctuation)
        try:
            db_desc = self.df_all_db_info[self.df_all_db_info["db_name"] == self.db_name].iloc[0]["db_description"]
        except IndexError:
            self.logger.info(f"\042{self.db_name}\042 is not in the database list hosted at PhysioNet!")
            return None
        db_desc = re.sub(f"[{punct}]+", "", db_desc).lower()
        db_desc = re.sub("[\\s:]+", "-", db_desc)
        url = posixpath.join(domain, f"{self.db_name}/{db_desc}-{self.version}.zip")
        if requests.head(url).headers.get("Content-Type") == "application/zip":
            self._url_compressed = url
        else:
            new_url = posixpath.join(wfdb.io.download.PN_INDEX_URL, f"{self.db_name}/get-zip/{self.version}")
            print(f"{url} is not available, try {new_url} instead")
        return self._url_compressed

    def download(self, compressed: bool = True) -> None:
        """Download the database from PhysioNet."""
        if compressed:
            if self.url_ is not None:
                http_get(self.url_, self.db_dir, extract=True)
                self._ls_rec()
                return
            else:
                self.logger.info("No compressed database available! Downloading the uncompressed version...")
        wfdb.dl_database(
            self.db_name,
            self.db_dir,
            keep_subdirs=True,
            overwrite=False,
        )
        self._ls_rec()


class NSRRDataBase(_DataBase):
    """Base class for readers for the NSRR database.

    For a full list of available databases, and their descriptions,
    please visit the NSRR database webpage [1]_.

    Parameters
    ----------
    db_name : str
        Name of the database.
    db_dir : str or pathlib.Path, optional
        Local storage path of the database.
    working_dir : str, optional
        Working directory, to store intermediate files and log files.
    verbose : int, default 1
        Verbosity level for logging.
    kwargs : dict, optional
        Auxilliary key word arguments.

    References
    ----------
    .. [1] https://sleepdata.org/

    """

    def __init__(
        self,
        db_name: str,
        db_dir: Optional[Union[str, Path]] = None,
        working_dir: Optional[str] = None,
        verbose: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_name=db_name,
            db_dir=db_dir,
            working_dir=working_dir,
            verbose=verbose,
            **kwargs,
        )
        self.fs = kwargs.get("fs", None)
        self._all_records = None
        self.file_opened = None

        all_dbs = [
            [
                "shhs",
                "Multi-cohort study focused on sleep-disordered breathing and cardiovascular outcomes",
            ],
            ["mesa", ""],
            ["oya", ""],
            [
                "chat",
                "Multi-center randomized trial comparing early adenotonsillectomy to " "watchful waiting plus supportive care",
            ],
            [
                "heartbeat",
                "Multi-center Phase II randomized controlled trial that evaluates the effects "
                "of supplemental nocturnal oxygen or Positive Airway Pressure (PAP) therapy",
            ],
            # more to be added
        ]
        self.df_all_db_info = pd.DataFrame(
            {
                "db_name": [item[0] for item in all_dbs],
                "db_description": [item[1] for item in all_dbs],
            }
        )
        self.kwargs = kwargs

    def safe_edf_file_operation(
        self,
        operation: str = "close",
        full_file_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """Safe IO operation for edf file.

        Parameters
        ----------
        operation : {"open", "close"}, optional
            Operation name, by default "close".
        full_file_path : str or pathlib.Path, optional
            Path of the file which contains the data.
            If is None, default path will be used.

        Returns
        -------
        None

        Raises
        ------
        ValueError
            If the operation is not supported.

        """
        if operation == "open":
            if self.file_opened is not None:
                self.file_opened._close()
            self.file_opened = EdfReader(str(full_file_path))
        elif operation == "close":
            if self.file_opened is not None:
                self.file_opened._close()
                self.file_opened = None
        else:
            raise ValueError("Illegal operation")

    def get_subject_id(self, rec: Union[str, int]) -> int:
        """Attach a unique subject ID for the record.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.

        Returns
        -------
        int
            Subject ID associated with the record.

        """
        raise NotImplementedError

    def show_rec_stats(self, rec: Union[str, int]) -> None:
        """Print the statistics about the record.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.

        Returns
        -------
        None

        """
        raise NotImplementedError

    def helper(self, items: Union[List[str], str, type(None)] = None) -> None:
        """Print corr. meanings of symbols belonging to `items`.

        Parameters
        ----------
        items : str or List[str], optional
            Items to print.
            If is None, then a comprehensive printing
            of meanings of all symbols will be performed.

        Returns
        -------
        None

        """
        pp = pprint.PrettyPrinter(indent=4)

        attrs = vars(self)
        methods = [
            func for func in dir(self) if callable(getattr(self, func)) and not (func.startswith("__") and func.endswith("__"))
        ]

        if items is None:
            _items = [
                "attributes",
                "methods",
            ]
        elif isinstance(items, str):
            _items = [items]
        else:
            _items = items

        pp = pprint.PrettyPrinter(indent=4)

        if "attributes" in _items:
            print("--- helpler - attributes ---")
            pp.pprint(attrs)
        if "methods" in _items:
            print("--- helpler - methods ---")
            pp.pprint(methods)


class CPSCDataBase(_DataBase):
    """Base class for readers for the CPSC database.

    Parameters
    ----------
    db_name : str
        Name of the database.
    db_dir : str or pathlib.Path, optional
        Local storage path of the database.
    working_dir : str, optional
        Working directory, to store intermediate files and log files.
    verbose : int, default 1
        Verbosity level for logging.
    kwargs : dict, optional
        Auxilliary key word arguments.

    """

    def __init__(
        self,
        db_name: str,
        db_dir: Optional[Union[str, Path]] = None,
        working_dir: Optional[str] = None,
        verbose: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            db_name=db_name,
            db_dir=db_dir,
            working_dir=working_dir,
            verbose=verbose,
            **kwargs,
        )
        self.fs = kwargs.get("fs", None)
        self._all_records = None

        self.kwargs = kwargs

    def get_subject_id(self, rec: Union[str, int]) -> int:
        """Attach a unique subject ID for the record.

        Parameters
        ----------
        rec : str or int
            Record name or index of the record in :attr:`all_records`.

        Returns
        -------
        int
            Subject ID associated with the record.

        """
        raise NotImplementedError

    def helper(self, items: Union[List[str], str, type(None)] = None) -> None:
        """Print corr. meanings of symbols belonging to `items`.

        Parameters
        ----------
        items : str or List[str], optional
            Items to print.
            If is None, then a comprehensive printing
            of meanings of all symbols will be performed.

        Returns
        -------
        None

        """
        pp = pprint.PrettyPrinter(indent=4)

        attrs = vars(self)
        methods = [
            func for func in dir(self) if callable(getattr(self, func)) and not (func.startswith("__") and func.endswith("__"))
        ]

        if items is None:
            _items = [
                "attributes",
                "methods",
            ]
        elif isinstance(items, str):
            _items = [items]
        else:
            _items = items

        pp = pprint.PrettyPrinter(indent=4)

        if "attributes" in _items:
            print("--- helpler - attributes ---")
            pp.pprint(attrs)
        if "methods" in _items:
            print("--- helpler - methods ---")
            pp.pprint(methods)

    def download(self) -> None:
        """Download the database from `self.url`."""
        if isinstance(self.url, str):
            http_get(self.url, self.db_dir, extract=True)
        else:
            for url in self.url:
                http_get(url, self.db_dir, extract=True)
        self._ls_rec()


@dataclass
class DataBaseInfo(CitationMixin):
    """A dataclass to store the information of a database.

    Attributes
    ----------
    title : str
        Title of the database.
    about : str or list of str
        Description of the database.
    usage : list of str
        Potential usages of the database.
    references : list of str
        References of the database.
    note : str or list of str, optional
        Notes of the database.
    issues : str or list of str, optional
        Known issues of the database.
    status : str, optional
        Status of the database.
    doi : str or list of str, optional
        DOI of the paper(s) describing the database.

    """

    title: str
    about: Union[str, Sequence[str]]
    usage: Sequence[str]
    references: Sequence[str]
    note: Optional[Union[str, Sequence[str]]] = None
    issues: Optional[Union[str, Sequence[str]]] = None
    status: Optional[str] = None
    doi: Optional[Union[str, Sequence[str]]] = None

    def format_database_docstring(self, indent: Optional[str] = None) -> str:
        """Format the database docstring from
        the information stored in the dataclass.

        The docstring will use the reStructuredText format.

        Parameters
        ----------
        indent : str, optional
            Indent of the docstring.
            If not specified, then 4 spaces will be used.

        Returns
        -------
        str
            The formatted docstring.

        NOTE
        ----
        An environment variable ``DB_BIB_LOOKUP`` can be set to
        ``True`` to enable the lookup of the bib entries.

        """
        if indent is None:
            indent = " " * 4
        title = textwrap.dedent(self.title).strip("\n ")
        if isinstance(self.about, str):
            about = "ABOUT\n-----\n" + textwrap.dedent(self.about).strip("\n ")
        else:
            about = ["ABOUT", "-----"] + [f"{idx+1}. {line}" for idx, line in enumerate(self.about)]
            about = "\n".join(about)
        if self.note is None:
            # note = "NOTE\n----"
            note = ""
        elif isinstance(self.note, str):
            note = "NOTE\n----\n" + textwrap.dedent(self.note).strip("\n ")
        else:
            note = ["NOTE", "----"] + [f"{idx+1}. {line}" for idx, line in enumerate(self.note)]
            note = "\n".join(note)
        if self.issues is None:
            # issues = "Issues\n------"
            issues = ""
        elif isinstance(self.issues, str):
            issues = "Issues\n------\n" + textwrap.dedent(self.issues).strip("\n ")
        else:
            issues = ["Issues", "-" * 6] + [f"{idx+1}. {line}" for idx, line in enumerate(self.issues)]
            issues = "\n".join(issues)
        references = ["References", "-" * 10] + [
            # f"""{idx+1}. <a name="ref{idx+1}"></a> {line}"""
            f""".. [{idx+1}] {line}"""
            for idx, line in enumerate(self.references)
        ]
        references = "\n".join(references)
        usage = ["Usage", "------"] + [f"{idx+1}. {line}" for idx, line in enumerate(self.usage)]
        usage = "\n".join(usage)

        docstring = textwrap.indent(
            f"""\n{title}\n\n{about}\n\n{note}\n\n{usage}\n\n{issues}\n\n{references}\n""",
            indent,
        )

        if self.status is not None and len(self.status) > 0:
            docstring = f"{self.status}\n\n{docstring}"

        lookup = os.getenv("DB_BIB_LOOKUP", False)
        citation = self.get_citation(lookup=lookup, print_result=False)
        if citation.startswith("@"):
            citation = textwrap.indent(citation, indent)
            citation = textwrap.indent(f"""Citation\n--------\n.. code-block:: bibtex\n\n{citation}""", indent)
            docstring = f"{docstring}\n\n{citation}\n"
        elif not lookup:
            citation = textwrap.indent(f"""Citation\n--------\n{citation}""", indent)
            docstring = f"{docstring}\n\n{citation}\n"

        return docstring


class PSGDataBaseMixin:
    """A mixin class for PSG databases.

    Contains methods for

        - convertions between sleep stage intervals and sleep stage masks
        - hypnogram plotting

    """

    def sleep_stage_intervals_to_mask(
        self,
        intervals: Dict[str, List[List[int]]],
        fs: Optional[int] = None,
        granularity: int = 30,
        class_map: Optional[Dict[str, int]] = None,
    ) -> np.ndarray:
        """Convert sleep stage intervals to sleep stage mask.

        Parameters
        ----------
        intervals : dict
            Sleep stage intervals, in the format of dict of list of lists of int.
            Keys are sleep stages and
            values are lists of lists of start and end indices of the sleep stages.
        fs : int, optional
            Sampling frequency corresponding to the sleep stage intervals,
            defaults to the sampling frequency of the database.
        granularity : int, default 30
            Granularity of the sleep stage mask, with units in seconds.
        class_map : dict, optional
            A dictionary mapping sleep stages to integers.
            If the database reader does not have a `sleep_stage_names` attribute,
            this parameter must be provided.

        Returns
        -------
        numpy.ndarray
            Sleep stage mask.

        """
        fs = fs or self.fs
        assert fs is not None and fs > 0, "`fs` must be positive"
        assert granularity > 0, "`granularity` must be positive"
        if not hasattr(self, "sleep_stage_names"):
            assert class_map is not None, "`class_map` must be provided"
        else:
            class_map = class_map or {k: len(self.sleep_stage_names) - i - 1 for i, k in enumerate(self.sleep_stage_names)}
        intervals = {
            class_map[k]: [[int(round(s / fs / granularity)), int(round(e / fs / granularity))] for s, e in v]
            for k, v in intervals.items()
        }
        intervals = {k: [[s, e] for s, e in v if s < e] for k, v in intervals.items()}
        intervals = {k: v for k, v in intervals.items() if len(v) > 0}
        siglen = max([e for v in intervals.values() for s, e in v])
        mask = np.zeros(siglen, dtype=int)
        for k, v in intervals.items():
            for s, e in v:
                mask[s:e] = k
        return mask

    def plot_hypnogram(
        self,
        mask: np.ndarray,
        granularity: int = 30,
        class_map: Optional[Dict[str, int]] = None,
        **kwargs,
    ) -> tuple:
        """Hypnogram visualization.

        Parameters
        ----------
        mask : numpy.ndarray
            Sleep stage mask.
        granularity : int, default 30
            Granularity of the sleep stage mask to be plotted,
            with units in seconds.
        class_map : dict, optional
            A dictionary mapping sleep stages to integers.
            If the database reader does not have a `sleep_stage_names` attribute,
            this parameter must be provided.
        kwargs : dict, optional
            Additional keyword arguments passed to :meth:`matplotlib.pyplot.plot`.

        Returns
        -------
        fig : matplotlib.figure.Figure
            Figure object.
        ax : matplotlib.axes.Axes
            Axes object.

        """
        if not hasattr(self, "sleep_stage_names"):
            pass
        else:
            class_map = class_map or {k: len(self.sleep_stage_names) - i - 1 for i, k in enumerate(self.sleep_stage_names)}

        if "plt" not in globals():
            import matplotlib.pyplot as plt

        fig_width = len(mask) * granularity / 3600 / 6 * 20  # stardard width is 20 for 6 hours

        fig, ax = plt.subplots(figsize=(fig_width, 4))
        color = kwargs.pop("color", "black")
        ax.plot(mask, color=color, **kwargs)

        # xticks to the format of HH:MM, every half hour
        xticks = np.arange(0, len(mask), 1800 / granularity)
        xticklabels = [f"{int(i * granularity / 3600):02d}:{int(i * granularity / 60 % 60):02d}" for i in xticks]
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels, fontsize=14)
        ax.set_xlabel("Time", fontsize=18)
        ax.set_xlim(0, len(mask))
        # yticks to the format of sleep stages
        yticks = sorted(class_map.values())
        yticklabels = [k for k, v in sorted(class_map.items(), key=lambda x: x[1])]
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels, fontsize=14)
        ax.set_ylabel("Sleep Stage", fontsize=18)

        return fig, ax


DEFAULT_FIG_SIZE_PER_SEC = 4.8


@dataclass
class BeatAnn:
    """Dataclass for beat annotation.

    Attributes
    ----------
    index : int
        Index of the beat.
    symbol : str
        Symbol of the beat.

    Properties
    ----------
    name : str
        Name of the beat.

    """

    index: int
    symbol: str

    @property
    def name(self) -> str:
        if self.symbol in WFDB_Beat_Annotations:
            return WFDB_Beat_Annotations[self.symbol]
        return WFDB_Non_Beat_Annotations.get(self.symbol, self.symbol)


# configurations for visualization
_PlotCfg = CFG()
# used only when corr. values are absent
# all values are time bias w.r.t. corr. peaks, with units in ms
_PlotCfg.p_onset = -40
_PlotCfg.p_offset = 40
_PlotCfg.q_onset = -20
_PlotCfg.s_offset = 40
_PlotCfg.qrs_radius = 60
_PlotCfg.t_onset = -100
_PlotCfg.t_offset = 60
