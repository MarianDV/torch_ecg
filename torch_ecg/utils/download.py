"""
utilities for downloading and extracting compressed data files

For most PhysioNet databases, the WFDB package already has a method `dl_database`
for downloading the data files.

"""

import os
import re
import shutil
import tarfile
import tempfile
import urllib
import warnings
import zipfile
from pathlib import Path
from typing import Iterable, Optional, Union

import requests
from tqdm.auto import tqdm

__all__ = [
    "http_get",
]


PHYSIONET_DB_VERSION_PATTERN = "\\d+\\.\\d+\\.\\d+"


def http_get(
    url: str,
    dst_dir: Union[str, Path],
    proxies: Optional[dict] = None,
    extract: bool = True,
    filename: Optional[str] = None,
) -> None:
    """Get contents of a URL and save to a file.

    This function is a modified version of the `download_file` function in
    `transformers.file_utils` [1]_.

    Parameters
    ----------
    url : str
        URL to download file from.
    dst_dir : str or pathlib.Path
        Directory to save the file.
    proxies : dict, optional
        Dictionary of proxy settings.
    extract : bool, default True
        Whether to extract the downloaded file.
    filename : str, optional
        Name of the file to save.
        If None, the filename will be the same as the URL.

    Returns
    -------
    None

    References
    ----------
    .. [1] https://github.com/huggingface/transformers/blob/master/src/transformers/file_utils.py

    """
    if filename is not None:
        assert not (Path(dst_dir) / filename).exists(), "file already exists"
    print(f"Downloading {url}.")
    if not is_compressed_file(url) and extract:
        if filename is not None:
            if not is_compressed_file(filename):
                warnings.warn(
                    "filename is given, and it is not a `zip` file or a compressed `tar` file. "
                    "Automatic decompression is turned off.",
                    RuntimeWarning,
                )
                extract = False
            else:
                pass
        else:
            warnings.warn(
                "URL must be pointing to a `zip` file or a compressed `tar` file. "
                "Automatic decompression is turned off. "
                "The user is responsible for decompressing the file manually.",
                RuntimeWarning,
            )
            extract = False
    # for example "https://www.dropbox.com/s/xxx/test%3F.zip??dl=1"
    # produces pure_url = "https://www.dropbox.com/s/xxx/test?.zip"
    pure_url = urllib.parse.unquote(url.split("?")[0])
    parent_dir = Path(dst_dir).parent
    df_suffix = _suffix(pure_url) if filename is None else _suffix(filename)
    downloaded_file = tempfile.NamedTemporaryFile(
        dir=parent_dir,
        suffix=df_suffix,
        delete=False,
    )
    req = requests.get(url, stream=True, proxies=proxies)
    content_length = req.headers.get("Content-Length")
    total = int(content_length) if content_length is not None else None
    if req.status_code == 403 or req.status_code == 404:
        raise Exception(f"Could not reach {url}.")
    progress = tqdm(unit="B", unit_scale=True, total=total, dynamic_ncols=True, mininterval=1.0)
    for chunk in req.iter_content(chunk_size=1024):
        if chunk:  # filter out keep-alive new chunks
            progress.update(len(chunk))
            downloaded_file.write(chunk)
    progress.close()
    downloaded_file.close()
    if extract:
        if ".zip" in df_suffix:
            _unzip_file(str(downloaded_file.name), str(dst_dir))
        elif ".tar" in df_suffix:  # tar files
            _untar_file(str(downloaded_file.name), str(dst_dir))
        else:
            os.remove(downloaded_file.name)
            raise Exception(f"Unknown file type {df_suffix}")
        # avoid the case the compressed file is a folder with the same name
        # DO NOT use _stem(Path(pure_url))
        if filename is None:
            _folder = Path(url).name.replace(_suffix(url), "")
        else:
            _folder = _stem(Path(filename))
        if _folder in os.listdir(dst_dir):
            tmp_folder = str(dst_dir).rstrip(os.sep) + "_tmp"
            os.rename(dst_dir, tmp_folder)
            os.rename(Path(tmp_folder) / _folder, dst_dir)
            shutil.rmtree(tmp_folder)
    else:
        Path(dst_dir).mkdir(parents=True, exist_ok=True)
        if filename is None:
            shutil.copyfile(downloaded_file.name, Path(dst_dir) / Path(pure_url).name)
        else:  # filename is not None
            shutil.copyfile(downloaded_file.name, Path(dst_dir) / filename)
    os.remove(downloaded_file.name)


def _stem(path: Union[str, Path]) -> str:
    """Get filename without extension,
    especially for .tar.xx files.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the file

    Returns
    -------
    str
        Filename without extension.

    """
    ret = Path(path).stem
    if Path(ret).suffix in [".tar", ".gz", ".bz2", ".xz", ".zip", ".7z"]:
        return _stem(ret)
    return ret


def _suffix(path: Union[str, Path], ignore_pattern: str = PHYSIONET_DB_VERSION_PATTERN) -> str:
    """Get file extension, including all suffixes.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the file.
    ignore_pattern : str, optional
        Pattern to ignore in the filename,
        by default `PHYSIONET_DB_VERSION_PATTERN`.

    Returns
    -------
    str
        The full file extension.

    """
    return "".join(Path(re.sub(ignore_pattern, "", str(path))).suffixes)


def is_compressed_file(path: Union[str, Path]) -> bool:
    """Check if the path points to a valid compressed file.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the file

    Returns
    -------
    bool
        True if the file is a valid compressed file,
        False otherwise.

    """
    compressed_file_pattern = "(\\.zip)|(\\.tar)"
    return re.search(compressed_file_pattern, _suffix(path)) is not None


def _unzip_file(path_to_zip_file: Union[str, Path], dst_dir: Union[str, Path]) -> None:
    """Unzips a .zip file to folder path.

    Parameters
    ----------
    path_to_zip_file : str or pathlib.Path
        Path to the .zip file.
    dst_dir : str or pathlib.Path
        Path to the destination folder.

    Returns
    -------
    None

    """
    print(f"Extracting file {path_to_zip_file} to {dst_dir}.")
    with zipfile.ZipFile(str(path_to_zip_file)) as zip_ref:
        zip_ref.extractall(str(dst_dir))


def _untar_file(path_to_tar_file: Union[str, Path], dst_dir: Union[str, Path]) -> None:
    """Decompress a .tar.xx file to folder path.

    Parameters
    ----------
    path_to_tar_file : str or pathlib.Path
        Path to the .tar.xx file.
    dst_dir : str or pathlib.Path
        Path to the destination folder.

    Returns
    -------
    None

    """
    print(f"Extracting file {path_to_tar_file} to {dst_dir}.")
    mode = Path(path_to_tar_file).suffix.replace(".", "r:").replace("tar", "").strip(":")
    with tarfile.open(str(path_to_tar_file), mode) as tar_ref:
        # tar_ref.extractall(str(dst_dir))
        # CVE-2007-4559 (related to  CVE-2001-1267):
        # directory traversal vulnerability in `extract` and `extractall` in `tarfile` module
        _safe_tar_extract(tar_ref, str(dst_dir))


def _is_within_directory(directory: Union[str, Path], target: Union[str, Path]) -> bool:
    """Check if the target is within the directory.

    Parameters
    ----------
    directory : str or pathlib.Path
        Directory to check.
    target : str or pathlib.Path
        Path to the target.

    Returns
    -------
    bool
        True if the target is within the directory,
        False otherwise.

    """
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)

    prefix = os.path.commonprefix([abs_directory, abs_target])

    return prefix == abs_directory


def _safe_tar_extract(
    tar: tarfile.TarFile,
    dst_dir: Union[str, Path],
    members: Optional[Iterable[tarfile.TarInfo]] = None,
    *,
    numeric_owner: bool = False,
) -> None:
    """Extract members from a tarfile **safely**
    to a destination directory.

    This function prevents path traversal attacks, by checking that the
    extracted files are within the destination directory.

    Parameters
    ----------
    tar : tarfile.TarFile
        The tarfile to extract from.
    dst_dir : str or pathlib.Path
        The destination directory
    members : Iterable[tarfile.TarInfo], optional
        The members to extract
        If is None, extract all members,
        otherwise, must be a subset of the list
        returned by :func:`tar.getmembers`.
    numeric_owner : bool, default False
        If True, only the numbers for user/group names are used
        and not the names. For more information,
        see :func:`tarfile.TarFile.extractall`.

    """
    for member in members or tar.getmembers():
        member_path = os.path.join(dst_dir, member.name)
        if not _is_within_directory(dst_dir, member_path):
            raise Exception("Attempted Path Traversal in Tar File")

    tar.extractall(dst_dir, members, numeric_owner=numeric_owner)
