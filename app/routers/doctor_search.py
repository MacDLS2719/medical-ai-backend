# app/routers/doctor_search.py

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.doctor_search import (
    DoctorSearchRequest,
    DoctorSearchResponse,
    DoctorSearchResult,
)
from app.services.doctor_search_service import doctor_search_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/doctor-search",
    tags=["Doctor Search"],
)


@router.post(
    "",
    response_model=DoctorSearchResponse,
    summary="Buscar médicos por especialidad y ubicación",
    description=(
        "Busca primero los médicos propios de la plataforma y, si faltan resultados, "
        "consulta fuentes externas."
    ),
)
async def search_doctors(
    payload: DoctorSearchRequest,
    db: Session = Depends(get_db),
) -> DoctorSearchResponse:
    try:
        search_data = await doctor_search_service.search(
            db,
            specialty=payload.specialty,
            specialties=payload.specialties,
            city=payload.city,
            country=payload.country,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_km=payload.radius_km,
            limit=payload.limit,
            search_mode=payload.search_mode,
        )

        results_list = search_data.get("results", [])
        validated_results = [
            DoctorSearchResult.model_validate(item)
            for item in results_list
        ]

        actual_mode = search_data.get("search_mode", payload.search_mode)
        count = len(validated_results)
        msg = (
            f"Se encontraron {count} especialistas en la base de datos."
            if actual_mode == "database"
            else f"Búsqueda web completada: {count} especialistas encontrados y guardados."
        )

        return DoctorSearchResponse(
            success=True,
            total=count,
            search_mode=actual_mode,
            center_latitude=search_data.get("center_latitude"),
            center_longitude=search_data.get("center_longitude"),
            results=validated_results,
            message=msg,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Error al buscar médicos")
        raise HTTPException(
            status_code=500,
            detail="No fue posible completar la búsqueda de médicos.",
        ) from exc


@router.post(
    "/external",
    response_model=DoctorSearchResponse,
    summary="Buscar médicos en la web externa y Google Maps (Mivor AI) y guardar en base de datos",
)
async def search_doctors_external(
    payload: DoctorSearchRequest,
    db: Session = Depends(get_db),
) -> DoctorSearchResponse:
    payload.search_mode = "external"
    return await search_doctors(payload, db)
