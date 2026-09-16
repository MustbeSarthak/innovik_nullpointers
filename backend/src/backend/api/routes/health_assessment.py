"""Health assessment (survey) endpoints — Module 1.

Endpoints
---------
``GET  /assessments/metadata``            survey steps, options and limits
``POST /assessments``                     submit the survey (create)
``GET  /assessments/me``                  retrieve the own assessment
``GET  /assessments/patient/{id}``        retrieve by ``patient_id``
``PUT  /assessments/me``                  replace the whole assessment
``PATCH /assessments/me``                 update selected sections
``DELETE /assessments/me``                withdraw the assessment

Every endpoint except ``/metadata`` requires the patient's bearer token and works
with the authenticated ``patient_id``, so a patient can only ever read or change
their own record.
"""

from fastapi import APIRouter, HTTPException, status

from backend.api.deps import CurrentPatient, DbSession
from backend.schemas.assessment import (
    HealthAssessmentCreate,
    HealthAssessmentRead,
    HealthAssessmentUpdate,
    SurveyMetadata,
)
from backend.services.assessment_service import (
    create_assessment,
    get_assessment,
    require_assessment,
    replace_assessment,
    to_read_model,
    update_assessment,
)
from backend.services.survey_metadata import build_survey_metadata

router = APIRouter(prefix="/assessments", tags=["Patient Health Assessment"])

ASSESSMENT_NOT_SUBMITTED = {
    "description": "The patient has not submitted a health assessment yet"
}


@router.get(
    "/metadata",
    response_model=SurveyMetadata,
    summary="Survey definition (steps, options, validation limits)",
)
def read_survey_metadata() -> SurveyMetadata:
    """Return the survey structure so clients stay in sync with validation."""
    return build_survey_metadata()


@router.post(
    "",
    response_model=HealthAssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a health assessment",
    responses={409: {"description": "The patient already has an assessment"}},
)
def submit_health_assessment(
    payload: HealthAssessmentCreate, patient: CurrentPatient, db: DbSession
) -> HealthAssessmentRead:
    """Store the patient's survey answers.

    Basic Information and Medical History are required; symptoms, medications,
    allergies and the additional-information field are optional.
    """
    assessment = create_assessment(db, patient.id, payload)
    return to_read_model(assessment)


@router.get(
    "/me",
    response_model=HealthAssessmentRead,
    summary="Retrieve the signed-in patient's assessment",
    responses={404: ASSESSMENT_NOT_SUBMITTED},
)
def read_own_health_assessment(
    patient: CurrentPatient, db: DbSession
) -> HealthAssessmentRead:
    """Return the health assessment of the authenticated patient."""
    assessment = require_assessment(db, patient.id)
    return to_read_model(assessment)


@router.get(
    "/patient/{patient_id}",
    response_model=HealthAssessmentRead,
    summary="Retrieve an assessment by patient id",
    responses={
        403: {"description": "The assessment belongs to another patient"},
        404: ASSESSMENT_NOT_SUBMITTED,
    },
)
def read_health_assessment_by_patient_id(
    patient_id: int,
    patient: CurrentPatient,
    db: DbSession,
) -> HealthAssessmentRead:
    """Return the assessment of ``patient_id`` for the owning patient.

    ``patient_id`` is the primary key of the existing patient record - the survey
    never creates patient rows of its own.
    """
    if patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only access your own health assessment",
        )
    assessment = require_assessment(db, patient.id)
    return to_read_model(assessment)


@router.put(
    "/me",
    response_model=HealthAssessmentRead,
    summary="Replace the whole health assessment",
    responses={404: ASSESSMENT_NOT_SUBMITTED},
)
def replace_own_health_assessment(
    payload: HealthAssessmentCreate, patient: CurrentPatient, db: DbSession
) -> HealthAssessmentRead:
    """Overwrite every section of the signed-in patient's assessment."""
    assessment = replace_assessment(db, patient.id, payload)
    return to_read_model(assessment)


@router.patch(
    "/me",
    response_model=HealthAssessmentRead,
    summary="Update selected survey sections",
    responses={404: ASSESSMENT_NOT_SUBMITTED},
)
def update_own_health_assessment(
    payload: HealthAssessmentUpdate, patient: CurrentPatient, db: DbSession
) -> HealthAssessmentRead:
    """Update only the sections present in the request body."""
    assessment = update_assessment(db, patient.id, payload)
    return to_read_model(assessment)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw the health assessment",
    responses={404: ASSESSMENT_NOT_SUBMITTED},
)
def delete_own_health_assessment(patient: CurrentPatient, db: DbSession) -> None:
    """Delete the signed-in patient's assessment without touching the account."""
    assessment = get_assessment(db, patient.id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health assessment has been submitted for this patient",
        )
    db.delete(assessment)
    db.commit()