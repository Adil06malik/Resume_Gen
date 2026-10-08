"""Compute a line-level diff between the original and tailored StructuredResume.

Used to show the user exactly which parts were tailored (added/changed/removed)
vs. kept unchanged.
"""

from app.schemas.resume import StructuredResume


def _skills_names(resume: StructuredResume):
    return [s.name for s in resume.skills]


def _section(title: str):
    return {"title": title, "lines": []}


def _line(text, status="unchanged", before=None, after=None):
    return {"text": text, "status": status, "before": before, "after": after}


def _simple_diff(orig_lines, new_lines):
    """Best-effort line diff returning (status) tuples preserving both sides."""
    result = []
    o_set = set(orig_lines)
    n_set = set(new_lines)
    for line in orig_lines:
        if line in n_set:
            result.append(_line(line, "unchanged"))
        else:
            result.append(_line(line, "removed"))
    for line in new_lines:
        if line in o_set:
            continue
        # find matching removed line position loosely
        result.append(_line(line, "added"))
    return result


def compute_diff(original: dict, tailored: dict) -> list:
    o = StructuredResume(**original)
    t = StructuredResume(**tailored)
    sections = []

    # Summary
    if t.summary:
        section = _section("Professional Summary")
        if o.summary == t.summary or not o.summary:
            section["lines"].append(_line(t.summary, "unchanged"))
        else:
            section["lines"].append(_line("Original", "unchanged"))
            section["lines"].append(_line(o.summary, "removed"))
            section["lines"].append(_line("Tailored", "unchanged"))
            section["lines"].append(_line(t.summary, "added"))
        sections.append(section)

    # Skills
    if t.skills:
        section = _section("Skills")
        o_skills = _skills_names(o)
        t_skills = _skills_names(t)
        for s in o_skills:
            section["lines"].append(_line(s, "removed" if s not in t_skills else "unchanged"))
        for s in t_skills:
            if s not in o_skills:
                section["lines"].append(_line(s, "added"))
        sections.append(section)

    # Experience
    if t.experience or o.experience:
        section = _section("Experience")
        # match roles by (title, company)
        o_by_role = {}
        for oe in o.experience:
            key = (oe.title, oe.company)
            o_by_role.setdefault(key, []).append(oe)
        for te in t.experience:
            key = (te.title, te.company)
            section["lines"].append(_line(f"{te.title} - {te.company}", "unchanged"))
            o_matches = o_by_role.get(key, [])
            o_bullets = []
            for om in o_matches:
                o_bullets.extend(om.description)
                if om.technologies and te.technologies:
                    o_bullets.extend([f"[tech] {x}" for x in om.technologies])
            # diff bullets
            o_set = set(o_bullets)
            for b in te.description:
                section["lines"].append(_line(b, "removed" if b in o_set else "added"))
            # show removed original bullets that were dropped
            remaining = [b for b in o_bullets if b not in te.description]
            for b in remaining:
                section["lines"].append(_line(b, "removed"))
        # removed roles
        t_roles = {(e.title, e.company) for e in t.experience}
        removed_roles = [(e.title, e.company) for e in o.experience if (e.title, e.company) not in t_roles]
        for role in removed_roles:
            section["lines"].append(_line(f"{role[0]} - {role[1]}", "removed"))
        if not section["lines"]:
            sections.pop()
        else:
            sections.append(section)

    # Projects
    if t.projects or o.projects:
        section = _section("Projects")
        o_names = [(p.name, p.description) for p in o.projects]
        for tp in t.projects:
            name_line = _line(tp.name, "added" if not any(p[0] == tp.name for p in o_names) else "unchanged")
            section["lines"].append(name_line)
            if tp.description and not any(p[0] == tp.name and p[1] == tp.description for p in o_names):
                section["lines"].append(_line(tp.description, "added"))
        sections.append(section)

    # Education
    if t.education:
        section = _section("Education")
        for te in t.education:
            section["lines"].append(_line(f"{te.degree} - {te.institution}", "unchanged"))
        sections.append(section)

    # Certifications
    if t.certifications:
        section = _section("Certifications")
        for tc in t.certifications:
            section["lines"].append(_line(f"{tc.name} - {tc.issuer}", "unchanged"))
        sections.append(section)

    return sections
