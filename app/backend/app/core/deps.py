from __future__ import annotations

from fastapi import Request


def get_settings(request: Request):
    return request.app.state.settings


def get_reports_repo(request: Request):
    return request.app.state.reports_repo


def get_run_repo(request: Request):
    return request.app.state.run_repo
