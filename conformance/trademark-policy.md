# ChangeSpec Naming and Attribution Policy

**Version:** 1.0 draft
**Effective:** 2026-04-16
**Owner:** Roboticforce Inc.

---

## Overview

"ChangeSpec" and "ChangeSpec Certified" are names used by Roboticforce Inc. for this specification and its conformance program. No trademark has been registered yet. This policy describes how we intend the names to be used as the project grows, and what we plan to register later.

The intent of this policy is to make the "ChangeSpec Certified" label meaningful over time. A label anyone can apply without meeting any standard communicates nothing. A label tied to a published conformance suite communicates that an implementation has been verified.

Until a registered mark exists, this document is a statement of intent. We ask the community to respect it in the same spirit.

---

## The Two Marks

### 1. "ChangeSpec" (Wordmark)

The bare wordmark "ChangeSpec" refers to the specification itself, the format, and the ChangeSpec ecosystem. It is descriptive of the technology.

### 2. "ChangeSpec Certified" (Certification Mark)

"ChangeSpec Certified" is a certification mark. It asserts that a specific implementation has passed the ChangeSpec conformance test suite at a defined level.

---

## Permitted Uses - No Certification Required

The following uses are permitted without any certification or approval:

- **Describing compatibility:** "This library reads and writes ChangeSpec 1.0 events."
- **Claiming format support:** "Supports ChangeSpec event format."
- **Documentation references:** Citing the ChangeSpec specification in documentation, blog posts, or tutorials.
- **"ChangeSpec Compatible" claim:** Any implementation the author believes conforms may claim "ChangeSpec Compatible" without running the formal test suite. This claim is on the author's own authority and does not carry the certification mark.
- **Open source implementations:** Building and publishing open source libraries that implement the ChangeSpec format.
- **Integration announcements:** Announcing that a product integrates with ChangeSpec-formatted feeds.
- **Academic and research use:** Referencing ChangeSpec in papers, research, or educational materials.

---

## Permitted Uses - Certification Required

The following claims require passing the conformance test suite at the corresponding level:

- **"ChangeSpec Certified"** (any form) requires Level 1 or higher certification.
- **"ChangeSpec Certified: Level N"** requires passing the test suite at that exact level.
- **The ChangeSpec Certified SVG badge** (from [conformance-badge.md](conformance-badge.md)) requires the corresponding level certification.
- **"Certified ChangeSpec Producer"** or **"ChangeSpec Certified Producer"** requires Level 4 producer certification.
- Any claim that implies independent verification or endorsement by Roboticforce Inc.

Self-certification (running the test suite yourself and reporting 0 failures) is sufficient for Levels 1-3. Level 4 requires official review.

---

## Claim Format Requirements

To avoid misleading claims, certified implementations must use the following formats:

| Correct | Incorrect |
|---|---|
| "ChangeSpec Certified: Level 2" | "ChangeSpec Certified" (without level) |
| "ChangeSpec Certified: Level 1 (Self-Certified)" | "Certified by ChangeSpec" |
| "ChangeSpec 1.0 Certified at Level 3" | "ChangeSpec Approved" |
| "ChangeSpec Certified Producer: Level 4" | "Official ChangeSpec Implementation" |

Claims must include the spec version and the level. Claims that imply higher authority than the certification warrants are not permitted.

---

## Prohibited Uses

The following uses are not permitted under any circumstances:

- Claiming "ChangeSpec Certified" without having passed the conformance test suite.
- Claiming a certification level that has not been achieved.
- Modifying the certification marks or creating derivative marks that could be confused with them.
- Using the marks in a way that implies Roboticforce Inc. endorses the implementation, its security, or its fitness for any particular purpose. Certification attests to conformance with the test suite only, not to security, correctness for production use, or any other property.
- Using the marks to disparage the ChangeSpec project, its maintainers, or other certified implementations.
- Registering domain names or social media handles that use "ChangeSpec Certified" as a primary identifier without authorization.

---

## Revocation

Roboticforce Inc. reserves the right to revoke certification and require cessation of mark use if:

- An implementation is found to have obtained certification fraudulently (e.g., by detecting vector inputs and hardcoding expected outputs).
- An implementation regresses and no longer passes the test suite at the claimed level, and the regression is not fixed within 60 days of notification.
- An implementation is found to have caused material harm to users who relied on the certification.

Revocation is communicated in writing to the registered contact for the certification. The implementation is given 30 days to respond before revocation takes effect, except in cases of fraud or immediate user harm.

---

## Enforcement

Roboticforce Inc. enforces this trademark policy to protect the integrity of the certification mark. Enforcement actions may include:

1. Informal notice requesting cessation of the improper use.
2. Formal cease-and-desist notice.
3. Legal action under applicable trademark law.

Roboticforce Inc. prioritizes good-faith resolutions. Most cases of improper mark use are the result of misunderstanding rather than bad faith and can be resolved through a correction notice.

To report a suspected trademark violation, email legal@changespec.com with the subject line "ChangeSpec Trademark Concern" and a description of the alleged violation.

---

## Fair Use

Nominative fair use of the "ChangeSpec" wordmark is permitted. Describing something as "a ChangeSpec parser," "a ChangeSpec event," or "compatible with ChangeSpec" is nominative use and is not restricted by this policy.

The test for nominative fair use:

1. The product or service cannot be readily identified without using the mark.
2. Only as much of the mark is used as is necessary for identification.
3. The use does not suggest sponsorship or endorsement by Roboticforce Inc.

---

## Contributor and Maintainer Use

Contributors to the ChangeSpec specification repository may identify themselves as "ChangeSpec contributor" or "ChangeSpec maintainer" in personal bios and professional profiles without certification. These are factual descriptions of a relationship to the open source project, not certification claims.

---

## Modeled On

This policy is modeled on the trademark policies of the OpenJS Foundation and the Cloud Native Computing Foundation (CNCF), adapted for a certification program rather than a project hosting organization. The intent is the same: make the mark meaningful, make the rules clear, and enforce them proportionately.

---

## Contact

- **Trademark questions:** legal@changespec.com
- **Certification program:** certify@changespec.com
- **Certification registry:** changespec.com/certified

---

## Changes to This Policy

Roboticforce Inc. may update this policy. Changes are announced on the ChangeSpec GitHub repository and at changespec.com/trademark. Changes to this policy do not retroactively revoke certifications already granted under prior versions; new requirements apply to new certification applications.
