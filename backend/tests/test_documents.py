import io

import config
from document_processor import extract_fields, safe_filename

NOTICE = b"""Patient ID: PT-9
Claim ID: RX-9
Medication: ExampleMed
Insurance: DemoHealth
Rejection Code: PA001
Rejection Message: Prior authorization required
Date of Service: 09/15/2026
"""


def upload(client, headers, filename, content, **data):
    return client.post("/api/upload", files={"file": (filename, io.BytesIO(content), "application/octet-stream")}, data=data, headers=headers)


def test_extract_fields_from_text():
    fields = extract_fields(NOTICE.decode())
    assert fields["patient_id"] == "PT-9"
    assert fields["rejection_code"] == "PA001"
    assert fields["rejection_message"] == "Prior authorization required"
    assert fields["date_of_service"] == "2026-09-15"


def test_safe_filename():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("my notice (1).txt") == "my_notice__1_.txt"


def test_upload_text_document(client, auth_headers):
    response = upload(client, auth_headers, "notice.txt", NOTICE)
    assert response.status_code == 201
    body = response.json()
    assert body["extracted_fields"]["medication"] == "ExampleMed"
    assert body["suggested_category"] == "Prior Authorization Required"


def test_upload_and_link_to_case(client, auth_headers):
    response = upload(client, auth_headers, "notice.txt", NOTICE, case_id="1")
    assert response.json()["linked_case_id"] == 1
    case = client.get("/api/cases/1", headers=auth_headers).json()
    assert any(d["filename"] == "notice.txt" for d in case["documents"])


def test_rejects_disallowed_extension(client, auth_headers):
    response = upload(client, auth_headers, "virus.exe", b"MZ....")
    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"]


def test_rejects_fake_pdf(client, auth_headers):
    response = upload(client, auth_headers, "fake.pdf", b"this is not a pdf")
    assert response.status_code == 400


def test_rejects_empty_file(client, auth_headers):
    assert upload(client, auth_headers, "empty.txt", b"").status_code == 400


def test_rejects_too_large_file(client, auth_headers, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)
    assert upload(client, auth_headers, "big.txt", b"x" * 100).status_code == 413


def test_upload_sample_pdf_and_docx(client, auth_headers):
    for name in ("sample_rejection_notice.pdf", "sample_rejection_notice.docx"):
        path = config.SAMPLE_DATA_DIR / name
        response = upload(client, auth_headers, name, path.read_bytes())
        assert response.status_code == 201, response.text
        assert response.json()["extracted_fields"]["rejection_code"] == "QL001"
