from __future__ import annotations

import hashlib
import html
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from janus_research.consent import ConsentRequiredError, ConsentStore
from janus_research.manifest import load_manifest
from janus_research.pipeline import RESEARCH_ROOT, experiment_directory, manifest_path
from janus_research.schema import ChallengeDefinition, DatasetSplit, PopulationClass, ResponseRecord
from janus_research.splits import SplitAssigner
from janus_research.storage import read_challenges, read_responses, write_responses

SUBJECT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,128}$")


def _latency_bucket(milliseconds: int) -> str:
    if milliseconds < 500:
        return "0-500"
    if milliseconds < 1500:
        return "500-1500"
    if milliseconds < 2500:
        return "1500-2500"
    return "2500+"


def render_challenge_html(challenge: ChallengeDefinition, sequence: int) -> str:
    public = challenge.to_public()
    payload = public.public_payload
    options = []
    for index, option in enumerate(payload["options"]):
        option_id = html.escape(str(option["id"]))
        label = html.escape(str(option.get("label", option_id)))
        visual = str(option.get("svg", ""))
        options.append(
            f'<label class="option"><input required type="radio" name="response" '
            f'value="{option_id}" accesskey="{index + 1}"><span>{visual}</span>'
            f"<strong>{label}</strong></label>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>JANUS local research study</title><style>
body{{font:18px system-ui;margin:2rem auto;max-width:900px;padding:0 1rem;color:#111827}}
.options{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem}}
.option{{border:2px solid #64748b;border-radius:8px;padding:1rem;display:grid;
gap:.5rem;cursor:pointer}}
.option:focus-within{{outline:4px solid #2563eb}} svg{{width:100%;max-height:180px}}
button{{margin-top:1.5rem;padding:.8rem 1.4rem;font:inherit}}
</style></head><body><main><p>Challenge {sequence + 1}</p>
<h1>{html.escape(str(payload["instruction"]))}</h1>
<p>{html.escape(str(payload.get("context", "")))}</p>
<form method="post"><input type="hidden" name="action" value="response">
<div class="options">{"".join(options)}</div>
<input type="hidden" name="revision_count" id="revisions" value="0">
<input type="hidden" name="input_modality" id="modality" value="unknown">
<button type="submit">Continue</button></form>
<form method="post"><input type="hidden" name="action" value="withdraw">
<button type="submit">Withdraw and exit</button></form></main><script>
let revisions=-1;
document.querySelectorAll('input[type=radio]').forEach(el=>el.addEventListener('change',()=>{{
revisions++; document.querySelector('#revisions').value=Math.max(0,revisions);}}));
document.addEventListener('keydown',()=>document.querySelector('#modality').value='keyboard',{{once:true}});
document.addEventListener('pointerdown',()=>document.querySelector('#modality').value='pointer',{{once:true}});
</script></body></html>"""


@dataclass
class StudyState:
    experiment_id: str
    protocol_version: str
    subject_id: str
    split: DatasetSplit
    challenges: list[ChallengeDefinition]
    output_path: Path
    consent_store: ConsentStore
    consent_document_version: str
    index: int = 0
    started_at: float = field(default_factory=time.monotonic)
    responses: list[ResponseRecord] = field(default_factory=list)

    def submit(self, response: str, revisions: int, modality: str) -> None:
        self.consent_store.require_active(self.subject_id)
        challenge = self.challenges[self.index]
        order = [str(option["id"]) for option in challenge.public_payload["options"]]
        if response not in order:
            raise ValueError("response is not a public option")
        latency = int((time.monotonic() - self.started_at) * 1000)
        self.responses.append(
            ResponseRecord(
                study_version=self.protocol_version,
                subject_id=self.subject_id,
                population_class=PopulationClass.HUMAN,
                condition="HUMAN_LOCAL",
                session_id=f"local_{self.subject_id}_{self.experiment_id}",
                challenge_id=challenge.challenge_id,
                challenge_family=challenge.family,
                generator_version=challenge.generator_version,
                seed_reference=hashlib.sha256(str(challenge.seed).encode()).hexdigest()[:24],
                sequence=self.index,
                public_option_order=order,
                response=response,
                response_latency_bucket=_latency_bucket(latency),
                revision_count=revisions,
                input_modality=modality,
                timestamp=datetime.now(UTC),
                split=self.split,
                challenge_split=challenge.split,
            )
        )
        self.index += 1
        self.started_at = time.monotonic()
        write_responses(self.responses, self.output_path)


def render_consent_html(document_version: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>JANUS study consent</title></head>
<body><main><h1>Research study consent</h1>
<p>This exploratory study records your choices, coarse response-time buckets,
input modality, and revision counts under a pseudonymous identifier. Participation is
voluntary. You may stop or withdraw; withdrawn data are excluded from analysis and raw
records are preserved pending the study's reviewed retention process.</p>
<p>Consent document version: {html.escape(document_version)}</p>
<form method="post"><input type="hidden" name="action" value="consent">
<label><input required type="checkbox" name="agree" value="yes"> I have read this
information and voluntarily agree to participate.</label><br>
<button type="submit">Agree and begin</button></form>
<p>Close this page to decline without creating a response record.</p></main></body></html>"""


def _handler(state: StudyState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str) -> None:
            encoded = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            try:
                state.consent_store.require_active(state.subject_id)
            except ConsentRequiredError:
                self._send(200, render_consent_html(state.consent_document_version))
                return
            if state.index >= len(state.challenges):
                self._send(200, "<h1>Study complete</h1><p>You may close this page.</p>")
                return
            self._send(200, render_challenge_html(state.challenges[state.index], state.index))

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                form = parse_qs(self.rfile.read(length).decode())
                action = form.get("action", [""])[0]
                if action == "consent":
                    if form.get("agree", [""])[0] != "yes":
                        raise ValueError("explicit consent is required")
                    state.consent_store.consent(
                        state.subject_id,
                        state.protocol_version,
                        state.consent_document_version,
                    )
                elif action == "withdraw":
                    state.consent_store.withdraw(state.subject_id)
                    self._send(200, "<h1>Withdrawal recorded</h1><p>You may close this page.</p>")
                    return
                elif action == "response":
                    state.submit(
                        form.get("response", [""])[0],
                        max(0, int(form.get("revision_count", ["0"])[0])),
                        form.get("input_modality", ["unknown"])[0],
                    )
                else:
                    raise ValueError("unknown form action")
            except (ConsentRequiredError, ValueError, IndexError) as error:
                self._send(400, f"<h1>Invalid response</h1><p>{html.escape(str(error))}</p>")
                return
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def run_study_server(experiment: str, subject: str, port: int) -> None:
    manifest = load_manifest(manifest_path(experiment))
    if not manifest.consent_document_version:
        raise ValueError("manifest has no consent document version")
    if "NEEDS_" in manifest.consent_document_version:
        raise ValueError("consent template still requires human review; collection is blocked")
    assigner = SplitAssigner(f"{manifest.experiment_id}:subjects", manifest.human_split_policy)
    subject_id = pseudonymous_subject_id(manifest.experiment_id, subject)
    subject_split = assigner.assign(subject_id)
    all_challenges = read_challenges(experiment_directory(manifest.experiment_id))
    challenges = [challenge for challenge in all_challenges if challenge.split == subject_split]
    if not challenges:
        raise ValueError(f"no generated challenges exist for assigned split {subject_split}")
    challenges = sorted(challenges, key=lambda challenge: challenge.challenge_id)[:9]
    collection_id = hashlib.sha256(subject_id.encode()).hexdigest()[:16]
    output = (
        RESEARCH_ROOT
        / "data"
        / "raw"
        / manifest.experiment_id
        / "local_collections"
        / collection_id
        / "responses.parquet"
    )
    prior_responses = read_responses(output) if output.exists() else []
    expected_prefix = [challenge.challenge_id for challenge in challenges[: len(prior_responses)]]
    if [record.challenge_id for record in prior_responses] != expected_prefix:
        raise RuntimeError("existing session does not match the current challenge sequence")
    state = StudyState(
        experiment_id=manifest.experiment_id,
        protocol_version=manifest.protocol_version,
        subject_id=subject_id,
        split=subject_split,
        challenges=challenges,
        output_path=output,
        consent_store=ConsentStore(
            RESEARCH_ROOT, manifest.experiment_id, manifest.retention_policy
        ),
        consent_document_version=manifest.consent_document_version,
        index=len(prior_responses),
        responses=prior_responses,
    )
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler(state))
    print(f"JANUS local study: http://127.0.0.1:{port}")
    print(f"Assigned split: {subject_split.value}; output: {output}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def pseudonymous_subject_id(experiment_id: str, subject: str) -> str:
    if not SUBJECT_PATTERN.fullmatch(subject):
        raise ValueError("subject must use letters, digits, '_' or '-'")
    return hashlib.sha256(f"{experiment_id}:{subject}".encode()).hexdigest()[:24]


def withdraw_subject(experiment: str, subject: str) -> Path:
    manifest = load_manifest(manifest_path(experiment))
    subject_id = pseudonymous_subject_id(manifest.experiment_id, subject)
    store = ConsentStore(RESEARCH_ROOT, manifest.experiment_id, manifest.retention_policy)
    return store.withdraw(subject_id).audit_path
