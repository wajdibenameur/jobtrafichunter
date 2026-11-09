import re

from app.modules.ai import SkillDefinition
from app.modules.profile.schemas import CandidateFields, Evidence, ProfilePayload
from app.shared.document import DocumentInspection


def propose_profile(document: DocumentInspection, terms: list[SkillDefinition]) -> ProfilePayload:
    fields = CandidateFields()
    evidence: dict[str, list[Evidence]] = {}
    warnings = ["RULE_BASED_REVIEW_REQUIRED"]
    if document.status == "NEEDS_OCR":
        warnings.append("OCR_UNAVAILABLE")
    for term in terms:
        path = "skills." + term.category
        for page in document.pages:
            match = next(
                (
                    m
                    for alias in [term.canonical, *term.aliases]
                    if (
                        m := re.search(
                            r"(?<!\w)" + re.escape(alias) + r"(?!\w)", page.text, re.IGNORECASE
                        )
                    )
                ),
                None,
            )
            if match is None:
                continue
            values = fields.skills.setdefault(term.category, [])
            if term.canonical not in values:
                values.append(term.canonical)
                evidence.setdefault(path, []).append(
                    Evidence(
                        page=page.number, start=match.start(), end=match.end(), quote=match.group()
                    )
                )
            break
    # Only explicit labelled title/summary lines. A person's name, first line,
    # junior keyword or date interval is never guessed to be a title/experience.
    for page in document.pages:
        headers = list(
            re.finditer(
                r"(?im)^\s*(education|formations?|experiences?|expériences?(?: professionnelles?)?|"
                r"languages|langues|certifications?|skills|compétences|summary|profil)\s*:?\s*$",
                page.text,
            )
        )
        for index, header in enumerate(headers):
            label = header.group(1).casefold()
            field = (
                "education"
                if label.startswith(("education", "formation"))
                else "experiences"
                if label.startswith(("experience", "expérience"))
                else "languages"
                if label in {"languages", "langues"}
                else "certifications"
                if label.startswith("certification")
                else None
            )
            if field is None:
                continue
            end = headers[index + 1].start() if index + 1 < len(headers) else len(page.text)
            for line in re.finditer(r"[^\r\n]+", page.text[header.end() : end]):
                quote = line.group().strip()
                if not quote:
                    continue
                values = getattr(fields, field)
                if len(quote) > 1000 or len(values) >= 30:
                    if "EXTRACTION_LIMIT_REVIEW" not in warnings:
                        warnings.append("EXTRACTION_LIMIT_REVIEW")
                    continue
                values.append(quote)
                start = header.end() + line.start() + len(line.group()) - len(line.group().lstrip())
                evidence.setdefault(field, []).append(
                    Evidence(page=page.number, start=start, end=start + len(quote), quote=quote)
                )
        for field, label, maximum in (
            (
                "professional_title",
                r"(?:professional title|titre professionnel|poste recherché)",
                200,
            ),
            ("summary", r"(?:summary|résumé professionnel|professional summary)", 3000),
        ):
            match = re.search(r"(?im)^\s*" + label + r"\s*:\s*([^\n]+)", page.text)
            if match and getattr(fields, field) is None:
                value = match.group(1).strip()
                if len(value) <= maximum:
                    setattr(fields, field, value)
                    evidence[field] = [
                        Evidence(
                            page=page.number,
                            start=match.start(1),
                            end=match.end(1),
                            quote=match.group(1),
                        )
                    ]
    return ProfilePayload(
        fields=fields,
        evidence=evidence,
        warnings=warnings,
        origins={key: "EXTRACTED_MENTION" for key in evidence},
        taxonomy={term.canonical: term.revision for term in terms},
        document_parser_version=document.parser_version,
    )
