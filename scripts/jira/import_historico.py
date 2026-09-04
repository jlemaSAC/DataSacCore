#!/usr/bin/env python3
"""Importa una propuesta histórica a Jira Cloud conservando su jerarquía.

Por seguridad se ejecuta en modo simulación salvo que se indique --apply.
No intenta modificar fechas de creación: Jira no permite establecerlas mediante
su API estándar. Las fechas históricas y la evidencia quedan en la descripción.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

try:
    import certifi
except ImportError:  # pragma: no cover - depends on the Python distribution.
    certifi = None


class ManifestError(ValueError):
    """Indica que el manifiesto histórico no tiene la estructura esperada."""


@dataclass(frozen=True)
class JiraConfiguration:
    base_url: str
    email: str
    api_token: str
    project_key: str
    epic_issue_type: str
    story_issue_type: str
    subtask_issue_type: str


def adf_paragraph(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def adf_heading(text: str) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": 2},
        "content": [{"type": "text", "text": text}],
    }


def adf_bullet_list(values: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [adf_paragraph(value)],
            }
            for value in values
        ],
    }


def jira_description(item: dict[str, Any]) -> dict[str, Any]:
    """Construye la descripción funcional que se publica en Jira.

    La evidencia histórica del manifiesto se conserva para auditoría local, pero
    no forma parte de la descripción de una incidencia de trabajo.
    """
    description = item.get("jira_description") or item.get("description") or "Sin descripción."
    paragraphs = [paragraph.strip() for paragraph in description.split("\n\n") if paragraph.strip()]
    return {
        "type": "doc",
        "version": 1,
        "content": [adf_paragraph(paragraph) for paragraph in paragraphs],
    }


def activity_comment_description(activity: dict[str, Any]) -> dict[str, Any]:
    """Convierte una actividad histórica estructurada en un comentario Jira."""
    content: list[dict[str, Any]] = [adf_heading("Registro de actividad histórica")]
    for section, key in (
        ("Objetivo", "objective"),
        ("Resumen", "summary"),
    ):
        if value := activity.get(key):
            content.extend([adf_heading(section), adf_paragraph(value)])

    implementation = activity.get("implementation", {})
    if implementation:
        implementation_content: list[dict[str, Any]] = []
        for layer in ("frontend", "backend"):
            values = implementation.get(layer, [])
            if values:
                label = "Frontend" if layer == "frontend" else "Backend"
                implementation_content.extend([adf_paragraph(label), adf_bullet_list(values)])
        if implementation_content:
            content.extend([adf_heading("Implementación"), *implementation_content])

    for section, key in (
        ("Reglas y validaciones", "rules"),
        ("Verificación", "verification"),
    ):
        values = activity.get(key, [])
        if values:
            content.extend([adf_heading(section), adf_bullet_list(values)])

    if period := activity.get("period"):
        content.extend([adf_heading("Periodo"), adf_paragraph(period)])

    return {"type": "doc", "version": 1, "content": content}


def worklog_comment_description(activity: dict[str, Any]) -> dict[str, Any]:
    """Construye la descripción enriquecida de un registro de trabajo Jira."""
    worklog = activity["worklog"]
    # ADF espera el timestamp del elemento Fecha en milisegundos desde Epoch.
    timestamp = str(int(datetime.fromisoformat(worklog["started"]).timestamp() * 1000))
    content: list[dict[str, Any]] = [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Fecha: "},
                {"type": "date", "attrs": {"timestamp": timestamp}},
                {"type": "text", "text": "   Estado: "},
                {
                    "type": "status",
                    "attrs": {
                        "localId": str(uuid4()),
                        "text": "Finalizado",
                        "color": "green",
                    },
                },
            ],
        }
    ]
    for section, key in (("Objetivo", "objective"), ("Resumen", "summary")):
        if value := activity.get(key):
            content.extend([adf_heading(section), adf_paragraph(value)])

    implementation = activity.get("implementation", {})
    if implementation:
        implementation_content: list[dict[str, Any]] = []
        for layer in ("frontend", "backend"):
            values = implementation.get(layer, [])
            if values:
                label = "Frontend" if layer == "frontend" else "Backend"
                implementation_content.extend([adf_paragraph(label), adf_bullet_list(values)])
        if implementation_content:
            content.extend([adf_heading("Implementación"), *implementation_content])

    for section, key in (("Reglas y validaciones", "rules"), ("Verificación", "verification")):
        values = activity.get(key, [])
        if values:
            content.extend([adf_heading(section), adf_bullet_list(values)])

    if references := activity.get("references", []):
        content.extend([adf_heading("Referencias técnicas"), adf_bullet_list(references)])

    return {"type": "doc", "version": 1, "content": content}


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ManifestError(f"No existe el manifiesto: {path}") from error
    except json.JSONDecodeError as error:
        raise ManifestError(f"El manifiesto no es JSON válido: {error}") from error

    if not isinstance(manifest, dict):
        raise ManifestError("El manifiesto debe ser un objeto JSON.")
    if not isinstance(manifest.get("epic"), dict):
        raise ManifestError("El manifiesto debe incluir un objeto 'epic'.")
    if not isinstance(manifest.get("stories"), list) or not manifest["stories"]:
        raise ManifestError("El manifiesto debe incluir al menos una historia en 'stories'.")

    validate_item(manifest["epic"], "epic")
    for index, story in enumerate(manifest["stories"], start=1):
        validate_item(story, f"stories[{index}]")
        if not isinstance(story.get("tasks"), list) or not story["tasks"]:
            raise ManifestError(f"stories[{index}] debe incluir al menos una tarea.")
        for task_index, task in enumerate(story["tasks"], start=1):
            validate_item(task, f"stories[{index}].tasks[{task_index}]")

    return manifest


def validate_item(item: Any, location: str) -> None:
    if not isinstance(item, dict) or not isinstance(item.get("title"), str) or not item["title"].strip():
        raise ManifestError(f"{location} debe incluir un título no vacío.")


def jira_configuration(arguments: argparse.Namespace) -> JiraConfiguration:
    values = {
        "JIRA_BASE_URL": arguments.base_url or os.getenv("JIRA_BASE_URL"),
        "JIRA_EMAIL": arguments.email or os.getenv("JIRA_EMAIL"),
        "JIRA_API_TOKEN": arguments.api_token or os.getenv("JIRA_API_TOKEN"),
        "JIRA_PROJECT_KEY": arguments.project_key or os.getenv("JIRA_PROJECT_KEY"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ManifestError(f"Faltan variables o argumentos de Jira: {', '.join(missing)}")

    return JiraConfiguration(
        base_url=values["JIRA_BASE_URL"].rstrip("/"),
        email=values["JIRA_EMAIL"],
        api_token=values["JIRA_API_TOKEN"],
        project_key=values["JIRA_PROJECT_KEY"],
        epic_issue_type=arguments.epic_issue_type,
        story_issue_type=arguments.story_issue_type,
        subtask_issue_type=arguments.subtask_issue_type,
    )


def issue_payload(
    item: dict[str, Any],
    issue_type: str,
    configuration: JiraConfiguration,
    parent_key: str | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "project": {"key": configuration.project_key},
        "summary": item["title"],
        "issuetype": {"name": issue_type},
        "description": jira_description(item),
        "labels": sorted(set(["historico", "analytics", *item.get("labels", [])])),
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    return {"fields": fields}


def jira_ssl_context() -> ssl.SSLContext:
    """Usa un bundle CA explícito cuando Python no conoce el emisor corporativo."""
    ca_bundle = os.getenv("JIRA_CA_BUNDLE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def post_issue(configuration: JiraConfiguration, payload: dict[str, Any]) -> str:
    credentials = base64.b64encode(f"{configuration.email}:{configuration.api_token}".encode()).decode()
    request = Request(
        f"{configuration.base_url}/rest/api/3/issue",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30, context=jira_ssl_context()) as response:  # noqa: S310 -- URL comes from explicit Jira configuration.
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira respondió HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible conectar con Jira: {error.reason}") from error

    issue_key = result.get("key")
    if not issue_key:
        raise RuntimeError(f"Jira no devolvió la clave de la incidencia: {result}")
    return issue_key


def put_issue(configuration: JiraConfiguration, issue_key: str, payload: dict[str, Any]) -> None:
    credentials = base64.b64encode(f"{configuration.email}:{configuration.api_token}".encode()).decode()
    request = Request(
        f"{configuration.base_url}/rest/api/3/issue/{issue_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urlopen(request, timeout=30, context=jira_ssl_context()) as response:  # noqa: S310 -- URL comes from explicit Jira configuration.
            if response.status != 204:
                raise RuntimeError(f"Jira devolvió un estado inesperado al actualizar {issue_key}: {response.status}")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira respondió HTTP {error.code} al actualizar {issue_key}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible conectar con Jira: {error.reason}") from error


def request_jira(
    configuration: JiraConfiguration,
    path: str,
    method: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    credentials = base64.b64encode(f"{configuration.email}:{configuration.api_token}".encode()).decode()
    request = Request(
        f"{configuration.base_url}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=30, context=jira_ssl_context()) as response:  # noqa: S310 -- URL comes from explicit Jira configuration.
            raw_response = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jira respondió HTTP {error.code} en {path}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible conectar con Jira: {error.reason}") from error
    return json.loads(raw_response) if raw_response else {}


def adf_text(value: Any) -> str:
    if isinstance(value, dict):
        status_text = ""
        if value.get("type") == "status":
            status_text = str(value.get("attrs", {}).get("text", ""))
        return str(value.get("text", "")) + status_text + "".join(
            adf_text(item) for item in value.get("content", [])
        )
    if isinstance(value, list):
        return "".join(adf_text(item) for item in value)
    return ""


def add_activity_comment(configuration: JiraConfiguration, issue_key: str, activity: dict[str, Any]) -> bool:
    comments = request_jira(configuration, f"/rest/api/3/issue/{issue_key}/comment?maxResults=100", "GET")
    if any("Registro de actividad histórica" in adf_text(comment.get("body", {})) for comment in comments.get("comments", [])):
        return False
    request_jira(
        configuration,
        f"/rest/api/3/issue/{issue_key}/comment",
        "POST",
        {"body": activity_comment_description(activity)},
    )
    return True


def delete_activity_comments(configuration: JiraConfiguration, issue_key: str) -> list[str]:
    comments = request_jira(configuration, f"/rest/api/3/issue/{issue_key}/comment?maxResults=100", "GET")
    deleted: list[str] = []
    for comment in comments.get("comments", []):
        if "Registro de actividad histórica" not in adf_text(comment.get("body", {})):
            continue
        comment_id = str(comment["id"])
        request_jira(configuration, f"/rest/api/3/issue/{issue_key}/comment/{comment_id}", "DELETE")
        deleted.append(comment_id)
    return deleted


def add_activity_worklog(configuration: JiraConfiguration, issue_key: str, activity: dict[str, Any]) -> bool:
    worklog = activity.get("worklog")
    if not isinstance(worklog, dict) or not worklog.get("started") or not worklog.get("time_spent"):
        raise ManifestError(
            f"La subtarea '{issue_key}' requiere activity.worklog.started y activity.worklog.time_spent."
        )
    existing = request_jira(configuration, f"/rest/api/3/issue/{issue_key}/worklog?maxResults=100", "GET")
    if any(
        "Estado:" in adf_text(item.get("comment", {}))
        and "Finalizado" in adf_text(item.get("comment", {}))
        and "Objetivo" in adf_text(item.get("comment", {}))
        for item in existing.get("worklogs", [])
    ):
        return False
    request_jira(
        configuration,
        f"/rest/api/3/issue/{issue_key}/worklog?adjustEstimate=auto",
        "POST",
        {
            "comment": worklog_comment_description(activity),
            "started": worklog["started"],
            "timeSpent": worklog["time_spent"],
        },
    )
    return True


def is_historical_activity_worklog(worklog: dict[str, Any]) -> bool:
    text = adf_text(worklog.get("comment", {}))
    return "Estado:" in text and "Finalizado" in text and "Objetivo" in text


def update_activity_worklog(configuration: JiraConfiguration, issue_key: str, activity: dict[str, Any]) -> str:
    worklog = activity.get("worklog")
    if not isinstance(worklog, dict) or not worklog.get("started") or not worklog.get("time_spent"):
        raise ManifestError(
            f"La subtarea '{issue_key}' requiere activity.worklog.started y activity.worklog.time_spent."
        )
    existing = request_jira(configuration, f"/rest/api/3/issue/{issue_key}/worklog?maxResults=100", "GET")
    matches = [item for item in existing.get("worklogs", []) if is_historical_activity_worklog(item)]
    if len(matches) != 1:
        raise RuntimeError(
            f"Se esperaba un único registro histórico en {issue_key}; se encontraron {len(matches)}."
        )
    worklog_id = str(matches[0]["id"])
    request_jira(
        configuration,
        f"/rest/api/3/issue/{issue_key}/worklog/{worklog_id}?adjustEstimate=auto",
        "PUT",
        {
            "comment": worklog_comment_description(activity),
            "started": worklog["started"],
            "timeSpent": worklog["time_spent"],
        },
    )
    return worklog_id


def transition_to_listo(configuration: JiraConfiguration, issue_key: str) -> bool:
    transitions = request_jira(configuration, f"/rest/api/3/issue/{issue_key}/transitions", "GET")
    transition = next(
        (
            item
            for item in transitions.get("transitions", [])
            if item.get("to", {}).get("name", "").casefold() == "listo"
        ),
        None,
    )
    if transition is None:
        return False
    request_jira(
        configuration,
        f"/rest/api/3/issue/{issue_key}/transitions",
        "POST",
        {"transition": {"id": transition["id"]}},
    )
    return True


def print_plan(manifest: dict[str, Any]) -> None:
    print(f"Épica: {manifest['epic']['title']}")
    for story in manifest["stories"]:
        print(f"  Historia: {story['title']}")
        for task in story["tasks"]:
            print(f"    Subtarea: {task['title']}")


def import_manifest(manifest: dict[str, Any], configuration: JiraConfiguration) -> dict[str, Any]:
    result: dict[str, Any] = {"epic": None, "stories": []}
    epic_key = post_issue(configuration, issue_payload(manifest["epic"], configuration.epic_issue_type, configuration))
    result["epic"] = epic_key

    for story in manifest["stories"]:
        story_key = post_issue(configuration, issue_payload(story, configuration.story_issue_type, configuration, epic_key))
        task_keys = [
            post_issue(configuration, issue_payload(task, configuration.subtask_issue_type, configuration, story_key))
            for task in story["tasks"]
        ]
        result["stories"].append({"key": story_key, "tasks": task_keys})
    return result


def update_existing_manifest(manifest: dict[str, Any], configuration: JiraConfiguration) -> dict[str, list[str]]:
    updated: list[str] = []

    def update(item: dict[str, Any]) -> None:
        issue_key = item.get("issue_key")
        if not isinstance(issue_key, str) or not issue_key.strip():
            raise ManifestError(
                f"La incidencia '{item['title']}' no incluye issue_key para actualizarla."
            )
        payload = {
            "fields": {
                "summary": item["title"],
                "description": jira_description(item),
                "labels": sorted(set(["historico", "analytics", *item.get("labels", [])])),
            }
        }
        put_issue(configuration, issue_key, payload)
        updated.append(issue_key)

    update(manifest["epic"])
    for story in manifest["stories"]:
        update(story)
        for task in story["tasks"]:
            update(task)
    return {"updated": updated}


def add_activity_comments(manifest: dict[str, Any], configuration: JiraConfiguration) -> dict[str, list[str]]:
    created: list[str] = []
    skipped: list[str] = []
    for story in manifest["stories"]:
        for task in story["tasks"]:
            issue_key = task.get("issue_key")
            activity = task.get("activity")
            if not isinstance(issue_key, str) or not isinstance(activity, dict):
                raise ManifestError(
                    f"La subtarea '{task['title']}' requiere issue_key y activity para registrar la actividad."
                )
            if add_activity_comment(configuration, issue_key, activity):
                created.append(issue_key)
            else:
                skipped.append(issue_key)
    return {"created": created, "skipped": skipped}


def replace_activity_comments(manifest: dict[str, Any], configuration: JiraConfiguration) -> dict[str, list[str]]:
    created_worklogs: list[str] = []
    skipped_worklogs: list[str] = []
    transitioned: list[str] = []
    for story in manifest["stories"]:
        for task in story["tasks"]:
            issue_key = task.get("issue_key")
            activity = task.get("activity")
            if not isinstance(issue_key, str) or not isinstance(activity, dict):
                raise ManifestError(
                    f"La subtarea '{task['title']}' requiere issue_key y activity para reemplazar su actividad."
                )
            if add_activity_worklog(configuration, issue_key, activity):
                created_worklogs.append(issue_key)
            else:
                skipped_worklogs.append(issue_key)

    for story in manifest["stories"]:
        for task in story["tasks"]:
            if task.get("skip_transition"):
                continue
            issue_key = task["issue_key"]
            if transition_to_listo(configuration, issue_key):
                transitioned.append(issue_key)

    deleted_comments: list[str] = []
    for story in manifest["stories"]:
        for task in story["tasks"]:
            deleted_comments.extend(delete_activity_comments(configuration, task["issue_key"]))
    return {
        "created_worklogs": created_worklogs,
        "skipped_worklogs": skipped_worklogs,
        "transitioned": transitioned,
        "deleted_comments": deleted_comments,
    }


def update_activity_worklogs(manifest: dict[str, Any], configuration: JiraConfiguration) -> dict[str, list[str]]:
    updated: list[str] = []
    for story in manifest["stories"]:
        for task in story["tasks"]:
            issue_key = task.get("issue_key")
            activity = task.get("activity")
            if not isinstance(issue_key, str) or not isinstance(activity, dict):
                raise ManifestError(
                    f"La subtarea '{task['title']}' requiere issue_key y activity para actualizar su registro."
                )
            update_activity_worklog(configuration, issue_key, activity)
            updated.append(issue_key)
    return {"updated_worklogs": updated}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Archivo JSON con épica, historias y tareas.")
    parser.add_argument("--apply", action="store_true", help="Crea incidencias en Jira. Sin esta opción solo simula.")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Actualiza incidencias existentes con --apply; cada elemento debe incluir issue_key.",
    )
    parser.add_argument(
        "--add-activity-comments",
        action="store_true",
        help="Agrega un comentario de actividad a cada subtarea con --apply.",
    )
    parser.add_argument(
        "--replace-activity-comments",
        action="store_true",
        help="Crea worklogs, transiciona a Listo y elimina los comentarios históricos con --apply.",
    )
    parser.add_argument(
        "--update-activity-worklogs",
        action="store_true",
        help="Actualiza los registros de actividad existentes con --apply.",
    )
    parser.add_argument("--base-url", help="Ejemplo: https://organizacion.atlassian.net")
    parser.add_argument("--email", help="Correo de Jira Cloud.")
    parser.add_argument("--api-token", help="API token de Jira Cloud.")
    parser.add_argument("--project-key", help="Clave del proyecto de Jira.")
    parser.add_argument("--epic-issue-type", default="Epic")
    parser.add_argument("--story-issue-type", default="Story")
    parser.add_argument("--subtask-issue-type", default="Sub-task")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        manifest = read_manifest(arguments.manifest)
        if not arguments.apply:
            action = (
                "agregar comentarios de actividad"
                if arguments.add_activity_comments
                else "reemplazar comentarios por registros de actividad"
                if arguments.replace_activity_comments
                else "actualizar registros de actividad"
                if arguments.update_activity_worklogs
                else "actualizar"
                if arguments.update_existing
                else "crear"
            )
            print(f"SIMULACIÓN: no se enviará nada a Jira. Use --apply para {action} incidencias.")
            print_plan(manifest)
            return 0

        configuration = jira_configuration(arguments)
        result = (
            add_activity_comments(manifest, configuration)
            if arguments.add_activity_comments
            else replace_activity_comments(manifest, configuration)
            if arguments.replace_activity_comments
            else update_activity_worklogs(manifest, configuration)
            if arguments.update_activity_worklogs
            else update_existing_manifest(manifest, configuration)
            if arguments.update_existing
            else import_manifest(manifest, configuration)
        )
    except (ManifestError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
