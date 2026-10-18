"""Deprecated: Case ingestion and job tracking have moved to app.api.admin."""

from fastapi import APIRouter

router = APIRouter(tags=["jobs"])
