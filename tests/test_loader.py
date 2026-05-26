import pytest
from pathlib import Path

from acquireml.loader import DataLoader, ANTIBIOTIC_MAP


def test_antibiotic_map_complete():
    assert set(ANTIBIOTIC_MAP.keys()) == {"azm", "cip", "cfx"}
    for key, (rtab_file, label_col) in ANTIBIOTIC_MAP.items():
        assert rtab_file.endswith(".Rtab"), f"{key}: Rtab filename must end with .Rtab"
        assert label_col.endswith("_sr"), f"{key}: label column must end with _sr"


def test_invalid_antibiotic_raises():
    with pytest.raises(ValueError, match="antibiotic must be one of"):
        DataLoader(data_dir=".", antibiotic="penicillin")


def _write_synthetic_data(tmp_path: Path, antibiotic: str = "azm") -> None:
    rtab_file, label_col = ANTIBIOTIC_MAP[antibiotic]
    rtab_content = (
        "pattern_id ERR001 ERR002 ERR003 ERR004\n"
        "UNITIG_AAA 1 0 1 0\n"
        "UNITIG_GGG 0 1 1 0\n"
    )
    (tmp_path / rtab_file).write_text(rtab_content)

    meta_lines = [
        "Sample_ID,azm_sr,cip_sr,cfx_sr",
        "ERR001,1,0,1",
        "ERR002,0,1,0",
        "ERR003,1,1,1",
        "ERR004,,0,",  # missing azm_sr → dropped for azm target
    ]
    (tmp_path / "metadata.csv").write_text("\n".join(meta_lines) + "\n")


def test_load_shape_after_dropna(tmp_path):
    _write_synthetic_data(tmp_path, antibiotic="azm")
    loader = DataLoader(data_dir=tmp_path, antibiotic="azm")
    X, y = loader.load()

    assert X.shape == (3, 2), "ERR004 should be dropped (missing azm_sr)"
    assert len(y) == 3
    assert set(X.index) == {"ERR001", "ERR002", "ERR003"}


def test_load_label_column_name(tmp_path):
    _write_synthetic_data(tmp_path, antibiotic="azm")
    loader = DataLoader(data_dir=tmp_path, antibiotic="azm")
    _, y = loader.load()
    assert y.name == "azm_sr"


def test_load_values_are_binary(tmp_path):
    _write_synthetic_data(tmp_path, antibiotic="azm")
    loader = DataLoader(data_dir=tmp_path, antibiotic="azm")
    X, y = loader.load()
    assert set(X.values.flatten().tolist()).issubset({0, 1})
    assert set(y.tolist()).issubset({0, 1})


def test_load_raises_on_no_overlap(tmp_path):
    rtab_file = ANTIBIOTIC_MAP["azm"][0]
    (tmp_path / rtab_file).write_text("pattern_id SAMPLE_X\nUNITIG_1 1\n")
    (tmp_path / "metadata.csv").write_text("Sample_ID,azm_sr,cip_sr,cfx_sr\nERR999,1,0,1\n")
    loader = DataLoader(data_dir=tmp_path, antibiotic="azm")
    with pytest.raises(ValueError, match="No samples overlap"):
        loader.load()


def test_missing_zip_raises(tmp_path):
    loader = DataLoader.__new__(DataLoader)
    loader.data_dir = tmp_path
    loader.antibiotic = "azm"
    loader._rtab_filename, loader._label_col = ANTIBIOTIC_MAP["azm"]
    with pytest.raises(FileNotFoundError, match="archive.zip"):
        loader._ensure_extracted()
