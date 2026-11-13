# SPDX-License-Identifier: EUPL-1.2
"""Versionsangaben (beim Image-Build über Build-Args gesetzt)."""
import os

VERSION = os.environ.get("APP_VERSION", "dev")
GIT_SHA = os.environ.get("GIT_SHA", "")[:7]


def label() -> str:
    return f"XMR-Ledger {VERSION}" + (f" ({GIT_SHA})" if GIT_SHA else "")
