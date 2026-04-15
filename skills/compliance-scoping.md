# skills/compliance-scoping.md — Compliance Scoping

## When to Load

When ComplianceAgent determines checklist scope for a Gate 3 review. Load this skill when:
- ComplianceAgent is initializing for PHASE 6 (Gate 3 evaluation).
- SecurityAgent identifies a compliance-sensitive tag (`#pii`, `#payment`, `#healthcare`)
  during PHASE 0 and requests scope pre-classification.
- AuditAgent is writing the final compliance disposition to `engram/audit/`.

---

## Scope Classification

ComplianceAgent reads objective tags from `specs/active/functional.md` to determine scope.
Tags may be set explicitly by the user or inferred by OrchestratorAgent during PHASE 0.1–0.2
interview processing.

| Scope Level | Tags | Checklist Size | Gate 3 Required |
|---|---|---|---|
| `NONE` | No sensitive tags; internal tooling or docs only | 0 items | No — bypassed |
| `STANDARD` | `#api-change`, `#breaking-change`, general software | 5–10 items | Yes |
| `REGULATED` | `#data-privacy`, `#pii`, `#gdpr`, `#lgpd`, `#ccpa`, `#authentication`, `#authorization` | 15–20 items | Yes |
| `HIGH` | `#payment`, `#financial`, `#healthcare`, `#hipaa`, `#pci`, `#cross-border` | 20–30 items + legal disclaimer | Yes — GATE_VERDICT required |

Tag matching is case-insensitive and additive: a spec with both `#pii` and `#payment`
tags yields scope `HIGH` (highest matching level takes precedence).

---

## Decision Tree

ComplianceAgent traverses this decision tree in order. Stop at the first YES answer and
assign the corresponding scope. Document the path in the Gate 3 checklist header.

```
Q1: Does the objective involve personally identifiable information (PII)?
    Names, emails, government IDs, biometrics, location history, IP addresses?
    → YES → Q3
    → NO  → Q2

Q2: Does the objective involve any form of financial transaction, account balance,
    credit/debit, payment processing, or trading data?
    → YES → scope = HIGH (#financial) → load PCI-DSS + OWASP API Top 10
    → NO  → Q5

Q3: Does the objective involve health records, medical data, diagnoses, prescriptions,
    insurance claims, or any PHI as defined by HIPAA?
    → YES → scope = HIGH (#healthcare) → load HIPAA + GDPR/LGPD + OWASP
    → NO  → Q4

Q4: Does the objective involve cross-border data transfer (data leaving the jurisdiction
    of origin, e.g., EU → US, BR → EU)?
    → YES → scope = HIGH (#cross-border) → load GDPR/LGPD cross-border clauses
    → NO  → scope = REGULATED → load GDPR/LGPD or CCPA (per jurisdiction tag)

Q5: Does the objective modify authentication, authorization, session management,
    or credential handling?
    → YES → scope = REGULATED (#authentication) → load OWASP Top 10 + OWASP API Top 10
    → NO  → Q6

Q6: Does the objective introduce a breaking API change or deprecate a public interface?
    → YES → scope = STANDARD (#api-change) → load migration notes checklist
    → NO  → Q7

Q7: Is the objective limited to internal tooling, documentation, or developer experience
    (no user-facing data, no external API, no regulated domain)?
    → YES → scope = NONE → Gate 3 bypassed
    → NO  → scope = STANDARD → load base checklist
```

---

## GDPR / LGPD Checklist (15 Items)

Apply when scope is `REGULATED` or `HIGH` and objective tag includes `#gdpr`, `#lgpd`,
`#pii`, or `#data-privacy`. LGPD (Brazil) mirrors GDPR structure; differences are noted.

1. **Lawful basis identified**: Every data processing activity has a documented legal basis
   (consent, contract, legal obligation, vital interests, public task, or legitimate interest).
   LGPD adds "credit protection" as an additional basis.

2. **Consent mechanism implemented** (if consent is the lawful basis): Consent is freely
   given, specific, informed, and unambiguous. Withdrawal mechanism is as easy as giving
   consent. Pre-ticked boxes are not valid.

3. **Right to erasure (right to be forgotten)**: System provides a deletion endpoint or
   process that removes all personal data for a given data subject upon request within
   30 days (GDPR) / 15 days (LGPD). Backups are addressed in the retention policy.

4. **Data minimization**: Only data strictly necessary for the stated purpose is collected
   and processed. Objective scope review: confirm no fields collected "for future use."

5. **DPA contact documented**: Data Protection Authority contact is identified for the
   relevant jurisdiction (e.g., CNIL for France, ANPD for Brazil, ICO for UK).

6. **DPIA trigger evaluated**: A Data Protection Impact Assessment is required when
   processing is high-risk: large-scale profiling, systematic monitoring of public areas,
   processing special category data (health, biometrics, political opinions). If triggered,
   DPIA must be completed before go-live.

7. **Breach notification (72-hour rule)**: A data breach notification process is defined.
   Supervisory authority must be notified within 72 hours of becoming aware of a breach
   (GDPR). LGPD: notify ANPD and data subjects within a "reasonable timeframe" (guidance:
   72 hours for serious breaches).

8. **Cross-border transfer safeguards**: Any transfer of personal data outside the EEA
   (GDPR) or Brazil (LGPD) relies on an adequacy decision, Standard Contractual Clauses
   (SCCs), Binding Corporate Rules, or equivalent mechanism. Transfer mechanism is
   documented in the privacy notice.

9. **Data processor agreements (DPAs)**: All third-party vendors who process personal data
   on behalf of the controller have a signed Data Processing Agreement. Agreement includes:
   purpose limitation, security obligations, sub-processor rules, deletion on termination.

10. **Retention limits defined**: Each data category has a documented retention period.
    Data is deleted or anonymized at end of retention period. Retention schedule is
    reviewed annually.

11. **Subject access request (SAR) handling**: Process defined to respond to data subject
    access requests within 30 days (GDPR) / 15 days (LGPD). Response includes: categories
    of data held, processing purposes, recipients, retention periods, rights available.

12. **Pseudonymization applied where feasible**: Where data must be retained for analytics,
    direct identifiers are replaced with pseudonyms. Mapping table is stored separately with
    access controls. Note: pseudonymized data is still personal data under GDPR.

13. **Encryption at rest**: Personal data stores (databases, backups, object storage) use
    AES-256 or equivalent. Key management is documented (HSM or KMS preferred). Keys are
    not stored adjacent to the encrypted data.

14. **Privacy by design**: Privacy controls are built into system architecture from the
    start, not added as a post-hoc layer. SecurityAgent Gate 2 verdict must confirm no
    design-level privacy violations before Gate 3 can proceed.

15. **Audit trail for data access**: Every access to personal data (read, write, delete,
    export) is logged with: timestamp, user/service ID, data category accessed, purpose.
    Logs retained for the duration of the data retention period or 3 years minimum.

---

## CCPA Checklist (10 Items)

Apply when scope is `REGULATED` or `HIGH` and objective tag includes `#ccpa` or when
the deployment jurisdiction is California (US). CCPA applies to businesses meeting any
one of: >$25M annual revenue, >100K consumers' data processed annually, >50% revenue
from selling personal information.

1. **Consumer rights notice provided**: Privacy policy discloses: categories of personal
   information collected, purposes, whether data is sold or shared, consumer rights (know,
   delete, correct, opt-out, non-discrimination), and how to submit requests.

2. **Opt-out of sale/sharing implemented**: A "Do Not Sell or Share My Personal
   Information" link is present on the homepage and in the privacy policy. Opt-out is
   honored within 15 business days. Global Privacy Control (GPC) signals are respected.

3. **Non-discrimination enforced**: Consumers who exercise CCPA rights are not denied
   goods/services, charged different prices, or provided a different quality of service
   unless the price difference is directly related to the value of the consumer's data
   (financial incentive program with prior opt-in consent).

4. **Financial incentive disclosure**: Any loyalty program or financial incentive for
   sharing data must have a separate, specific opt-in consent and a disclosure of the
   data's reasonably calculated value.

5. **12-month lookback**: Responses to consumer "right to know" requests must cover
   personal information collected in the 12 months preceding the request.

6. **Authorized agent protocol**: Process defined to verify and respond to requests
   submitted by authorized agents acting on behalf of consumers. Agent must provide
   written permission from the consumer; business may require the consumer to directly
   confirm.

7. **Business threshold checks documented**: Legal/compliance team has confirmed which
   CCPA threshold(s) apply and documented the basis for CCPA compliance obligation.
   Threshold confirmation is refreshed annually.

8. **Service provider agreement in place**: All service providers who receive personal
   information have a signed contract prohibiting them from: selling or sharing the data,
   retaining or using it for their own commercial purpose, or using it outside the scope
   of the service agreement.

9. **Do-not-sell link requirement verified**: Link is present on every page of the website
   that collects personal information (not just the privacy policy page). Link is clearly
   labeled and accessible. Mobile app equivalent (in-app mechanism) is implemented.

10. **Annual training documented**: Employees who handle consumer requests or personal
    information receive annual CCPA training. Training records are maintained for audit
    purposes.

---

## HIPAA Checklist (12 Items)

Apply when scope is `HIGH` and objective tag includes `#healthcare` or `#hipaa`. PHI
(Protected Health Information) is individually identifiable health information in any form.

1. **PHI definition confirmed**: Review confirms which data elements qualify as PHI:
   18 HIPAA identifiers (name, geographic data, dates related to individual, phone,
   fax, email, SSN, MRN, health plan #, account #, certificate/license #, VIN, device
   identifiers, URLs, IP addresses, biometrics, photos, any other unique identifier).

2. **Minimum necessary standard applied**: Workforce members access only the minimum
   PHI necessary to perform their job function. System enforces role-based access
   controls; no "view all" default roles.

3. **Business Associate Agreement (BAA) in place**: Every vendor, contractor, or
   subcontractor that creates, receives, maintains, or transmits PHI on behalf of
   a covered entity has a signed BAA. BAA specifies permitted uses, safeguards required,
   and breach notification obligations.

4. **Access controls implemented**: Technical safeguards enforce unique user identification,
   automatic logoff, encryption and decryption controls. PHI systems require MFA for all
   non-emergency access.

5. **Audit logs — 6-year retention**: All access to PHI is logged (user, action, timestamp,
   PHI record). Logs are retained for a minimum of 6 years from creation or last effective
   date. Logs are tamper-evident (append-only or cryptographically signed).

6. **Encryption in transit**: All PHI transmitted over any network uses TLS 1.2 or higher.
   Certificate validation is enforced; self-signed certificates are not permitted in
   production.

7. **Encryption at rest**: PHI stored in databases, backups, and file systems uses
   AES-256. Encryption keys are managed separately from the data (HSM or KMS).

8. **Breach rule — 60-day notification**: Process defined for breach notification within
   60 days of discovery: notify affected individuals (written notice), HHS OCR (online
   portal), and if breach affects >500 residents of a state, prominent media outlets in
   that state. Breach log maintained for all breaches regardless of size.

9. **Workforce training**: All workforce members with PHI access complete HIPAA training
   at hire and annually thereafter. Training records retained for 6 years.

10. **Facility access controls**: Physical access to locations where PHI is stored or
    processed is controlled (badge access, visitor logs, workstation placement to prevent
    unauthorized viewing).

11. **Workstation and device security**: Workstations accessing PHI have screen lock
    after ≤5 min inactivity, full-disk encryption, and are covered by a device management
    policy. Mobile device management (MDM) enforced for any mobile device with PHI access.

12. **Contingency plan (disaster recovery)**: Data backup plan, disaster recovery plan,
    emergency mode operation plan, and testing/revision procedures are documented.
    Backups are tested for restorability at least annually. RPO and RTO are defined.

---

## PCI-DSS Checklist (10 Items)

Apply when scope is `HIGH` and objective tag includes `#payment`, `#financial`, or `#pci`.
PCI-DSS v4.0 requirements apply to any system that stores, processes, or transmits
cardholder data (CHD) or sensitive authentication data (SAD).

1. **Cardholder data environment (CDE) scope defined**: Network diagram identifies all
   system components in scope. Scope is reviewed annually and after any significant change.
   Systems that can impact the security of the CDE are in scope even if they do not directly
   process CHD.

2. **Network segmentation verified**: CDE is isolated from out-of-scope systems via
   firewalls, VLANs, or other controls. Segmentation controls are tested at least annually
   by penetration testing. Flat networks are not permitted.

3. **Strong cryptography for CHD in transit and at rest**: PAN (Primary Account Number)
   is never transmitted in cleartext. TLS 1.2+ required for all external and internal CHD
   transmission. Stored PAN is masked (show only first 6 / last 4 digits) or encrypted
   with strong cryptography. CVV2/CVC2 is never stored after authorization.

4. **Access control (need-to-know)**: Access to CHD is restricted to individuals whose job
   requires it. Unique user IDs are assigned; shared/generic accounts are prohibited.
   Access is reviewed at least every 6 months.

5. **MFA for non-console administrative access**: All non-console administrative access to
   the CDE and all remote access originating from outside the CDE require multi-factor
   authentication. Includes access via VPN, jump servers, and remote desktop.

6. **Vulnerability scanning — quarterly**: Internal and external vulnerability scans are
   performed at least quarterly by an Approved Scanning Vendor (ASV) for external scans.
   High and critical vulnerabilities are remediated before the next quarterly scan.

7. **Penetration testing — annual**: Internal and external penetration testing is performed
   at least annually and after any significant infrastructure or application change.
   Penetration test covers the entire CDE perimeter and critical systems.

8. **Log monitoring and SIEM**: All in-scope systems generate audit logs. Logs are reviewed
   daily (automated alerting is acceptable). Logs are retained for at least 12 months with
   3 months immediately available for analysis.

9. **Secure software development standards**: All custom code for the CDE is developed
   following secure coding guidelines. Code review by trained reviewers before deployment.
   Web-facing applications are protected by a WAF or undergo annual application penetration
   testing.

10. **Vendor/third-party management**: A list of all third-party service providers (TSPs)
    with access to CHD is maintained. TSPs provide annual written confirmation of PCI-DSS
    compliance (AOC or equivalent). Contracts define security responsibilities.

---

## OWASP API Top 10 (2023)

Apply when scope is `STANDARD`, `REGULATED`, or `HIGH` and the objective involves any
API endpoint. SecurityAgent must verify mitigations for each applicable item at Gate 2.

| ID | Name | Description | PIV/OAC Mitigation Action |
|---|---|---|---|
| API1 | Broken Object Level Authorization | API endpoint accepts user-supplied IDs without verifying the requesting user owns the object | SecurityAgent requires per-object authorization check in Gate 2 code review; `sec-gates` sub-agent flags missing ownership assertions |
| API2 | Broken Authentication | Weak authentication mechanisms, tokens with no expiry, missing MFA for sensitive operations | SecurityAgent verifies auth flows in PHASE 5; CROSS_ALERT if JWT expiry is missing or >24h for sensitive endpoints |
| API3 | Broken Object Property Level Authorization | API exposes more object properties than the client is authorized to see (over-exposure) | StandardsAgent checks response schemas for unexposed field leakage; SecurityAgent flags DTO/serializer misconfigurations |
| API4 | Unrestricted Resource Consumption | No rate limiting, request size limits, or query complexity limits on API | SecurityAgent Gate 2 checklist item: rate limiting middleware present and tested |
| API5 | Broken Function Level Authorization | Admin-only functions accessible to lower-privilege users due to missing role checks | `sec-gates` sub-agent reviews all admin endpoints for role enforcement in PHASE 5 |
| API6 | Unrestricted Access to Sensitive Business Flows | Automated abuse of business logic (e.g., mass account creation, bulk scraping) | SecurityAgent requires business-flow rate limiting and bot detection evidence in Gate 2 |
| API7 | Server-Side Request Forgery (SSRF) | API fetches a remote resource from a user-supplied URL without validation | SecurityAgent CROSS_ALERT if any user-controlled URL is passed to server-side HTTP client without allowlist |
| API8 | Security Misconfiguration | Missing security headers, verbose error messages, outdated libraries, unnecessary HTTP methods enabled | StandardsAgent checks security headers in Gate 2; `sec-integrity` verifies dependency versions |
| API9 | Improper Inventory Management | Outdated or undocumented API versions remain accessible in production | AuditAgent verifies API version registry is current; deprecated endpoints must return 410 |
| API10 | Unsafe Consumption of APIs | Service trusts data from third-party APIs without validation, enabling injection or logic attacks | SecurityAgent requires input validation on all third-party API responses; `sec-injection` runs `Vault.scanForInjection()` on external data |

---

## OWASP Top 10 (2021)

Apply when scope is `REGULATED` or `HIGH` and the objective involves web application
components. SecurityAgent must verify mitigations for each applicable item at Gate 2 and Gate 2b.

| ID | Name | Description | SecurityAgent Action |
|---|---|---|---|
| A01 | Broken Access Control | Users act outside their intended permissions (IDOR, path traversal, privilege escalation) | CROSS_ALERT on any missing authorization check; `sec-gates` sub-agent reviews all route-level access controls |
| A02 | Cryptographic Failures | Sensitive data exposed due to weak or missing encryption (cleartext passwords, weak TLS, deprecated algorithms) | `sec-integrity` verifies no use of MD5/SHA1 for sensitive operations; TLS version enforcement checked at Gate 2 |
| A03 | Injection | SQL, NoSQL, LDAP, OS, SSTI injection via untrusted input | `sec-injection` runs `Vault.scanForInjection()` on all LLM-generated code and all input surfaces; parameterized queries required |
| A04 | Insecure Design | Missing or ineffective security controls in system design; security not built in from architecture phase | SecurityAgent participates in PHASE 1 DAG review; insecure design patterns trigger ESCALATION before PHASE 5 |
| A05 | Security Misconfiguration | Default credentials, unnecessary features enabled, missing hardening, verbose error messages | `sec-comms` and StandardsAgent review configuration files; Gate 2 checklist requires hardening evidence |
| A06 | Vulnerable and Outdated Components | Using components with known CVEs; no component inventory | `sec-integrity` verifies dependency manifest against known CVE databases; components with CVSS ≥7.0 block Gate 2 |
| A07 | Identification and Authentication Failures | Credential stuffing, weak passwords, missing MFA, insecure session management | SecurityAgent Gate 2 evaluator requires auth implementation evidence; CROSS_ALERT on missing MFA for sensitive flows |
| A08 | Software and Data Integrity Failures | Unsigned updates, insecure deserialization, CI/CD pipeline integrity gaps | `sec-integrity` enforces SHA-256 + HMAC-SHA256 verification on all framework files; unsigned deployments rejected |
| A09 | Security Logging and Monitoring Failures | Missing logs for security events; no alerting on anomalous activity | AuditAgent verifies security event logging completeness; TelemetryLogger alert configuration reviewed at Gate 3 |
| A10 | Server-Side Request Forgery (SSRF) | Server fetches user-controlled URL without validation; enables cloud metadata access | SecurityAgent CROSS_ALERT on any user-controlled URL passed to server-side HTTP clients; allowlist enforcement required |

---

## License Compatibility Matrix

Apply when scope is `STANDARD`, `REGULATED`, or `HIGH` and the objective incorporates
third-party libraries. StandardsAgent must verify license compatibility before Gate 2b.

| License | Can Use in Project | Can Modify | Can Distribute | Commercial OK | Copyleft Effect |
|---|---|---|---|---|---|
| **MIT** | Yes | Yes | Yes | Yes | None — most permissive |
| **Apache 2.0** | Yes | Yes | Yes | Yes | None (patent grant included) |
| **GPL v3** | Yes (with condition) | Yes | Yes — under GPL v3 | Yes (if GPL-compliant) | Strong — entire project must be GPL v3 |
| **LGPL v2.1/v3** | Yes | Yes | Yes | Yes | Weak — only modifications to LGPL code must be LGPL; linking is permitted |
| **MPL 2.0** | Yes | Yes | Yes | Yes | File-level — only modified MPL files must remain MPL; new files can use different license |
| **AGPL v3** | Yes (with condition) | Yes | Yes — under AGPL v3 | Yes (if AGPL-compliant) | Strong + network — SaaS/API use triggers copyleft (source disclosure required) |

**PIV/OAC policy**: The framework itself uses MIT license. Third-party dependencies with
GPL v3 or AGPL v3 must be isolated (never statically linked or bundled) and flagged in
the Gate 2b report. AGPL v3 dependencies in server-side code require legal review before
inclusion.

---

## Dual-Use Assessment

SecurityAgent must evaluate dual-use potential for any objective tagged `#security-tool`,
`#cryptography`, `#data-collection`, or `#monitoring`. Dual-use code has legitimate
defensive applications but can also enable offensive operations.

SecurityAgent **must** issue GATE_VERDICT(REJECTED) and halt the session when any of the
following criteria are met:

1. **Cryptographic vulnerabilities**: Objective deliberately introduces a backdoor,
   weakened key generation, or non-standard algorithm designed to fail in predictable ways.
   Distinguishable from: implementing legacy algorithms for compatibility (acceptable with
   WARN) or demonstrating known-weak algorithms in a test harness (acceptable with
   documentation requirement).

2. **Surveillance capabilities**: Objective builds covert data collection (keyloggers,
   screen capture without user consent, microphone/camera access without disclosure,
   location tracking without opt-in). Legitimate monitoring with user consent and
   disclosure is acceptable; covert collection is not.

3. **Data harvesting at scale**: Objective harvests personal data from third-party systems
   without authorization (scraping in violation of ToS when that scraping collects PII,
   credential stuffing, mass account enumeration). Authorized penetration testing with
   written client permission is acceptable.

**Escalation path when dual-use is detected:**

```
SecurityAgent → GATE_VERDICT(REJECTED) at active gate
             → CROSS_ALERT broadcast to OrchestratorAgent + AuditAgent
             → AuditAgent writes rejection record to engram/audit/<session_id>_rejected.md
             → Session proceeds to PHASE 7 (documentation of rejection) then PHASE 8 (close)
             → No further code generation or LLM calls on the rejected objective
```

---

## Agent Response Protocol

ComplianceAgent selects its checklist and actions based on the scope level determined by
the decision tree above. SecurityAgent actions are scope-gated as shown below.

### NONE — Gate 3 Bypassed

- ComplianceAgent does not generate a checklist.
- Gate 3 evaluation is skipped. Staging → main merge permitted with only Gate 2b APPROVED.
- AuditAgent records the bypass decision in `engram/audit/<session_id>_gate3_bypass.md`
  including: scope determination rationale, tags evaluated, decision tree path taken.
- SecurityAgent: no additional compliance actions beyond standard Gate 2 / Gate 2b review.

### STANDARD — OWASP Check

- ComplianceAgent generates a 5–10 item checklist covering: functional requirements,
  test coverage, documentation, CHANGELOG, no regressions (EvaluationAgent ≥ 0.80).
- SecurityAgent: runs OWASP Top 10 spot-check for applicable items (A01, A03, A05 minimum)
  and OWASP API Top 10 if any API endpoints are introduced.
- Gate 3 GATE_VERDICT is issued by ComplianceAgent. APPROVED requires all checklist items
  confirmed. CONDITIONAL allowed for documentation gaps (must be resolved within 48h).
  REJECTED if functional requirements are not met or regressions detected.

### REGULATED — Full Checklist

- ComplianceAgent generates the full checklist for the applicable regulation(s):
  GDPR/LGPD (15 items) and/or CCPA (10 items), plus OWASP API Top 10 (10 items).
- SecurityAgent: complete OWASP Top 10 review (all 10 items), dual-use assessment,
  and injection scan coverage of all data input surfaces.
- Gate 3 GATE_VERDICT: APPROVED requires all 15+ checklist items confirmed.
  CONDITIONAL is not permitted for items 1 (lawful basis), 3 (erasure), 7 (breach rule),
  or 13 (encryption at rest) — these are BLOCKER items; any gap yields REJECTED.
  AuditAgent writes full disposition to `engram/audit/`.

### HIGH — GATE_VERDICT Required

- ComplianceAgent generates combined checklists: all applicable regulations (GDPR/LGPD +
  HIPAA and/or PCI-DSS) + OWASP Top 10 + OWASP API Top 10. Minimum 20 items.
- Legal disclaimer is appended to the checklist: "ComplianceAgent checklists are
  operational aids, not legal advice. For regulated industries: consult qualified counsel."
- SecurityAgent: full OWASP review, dual-use assessment, and explicit BAA / DPA / service
  provider agreement verification.
- Gate 3 GATE_VERDICT is mandatory: ComplianceAgent **must** issue an explicit
  GATE_VERDICT(APPROVED | REJECTED | CONDITIONAL). A missing verdict is treated as
  REJECTED by OrchestratorAgent.
- CONDITIONAL is permitted only for items in the "documentation" or "training" categories,
  with a written remediation plan and timeline (≤30 days). All technical and legal
  requirements must be APPROVED before GATE_VERDICT(CONDITIONAL) can be issued.
- REJECTED: session proceeds to PHASE 7 (documentation of rejection reason) then
  PHASE 8 (close). No deployment permitted until a new session resolves the rejection items.

---

## Legal Disclaimer

ComplianceAgent checklists are operational aids generated by an AI framework, not legal
advice. Checklist completion does not constitute legal compliance or regulatory certification.
For regulated industries (healthcare, financial services, legal): consult qualified counsel
before deployment. PIV/OAC framework authors assume no liability for compliance decisions
made on the basis of this skill.

<!-- v5.1 — expanded from v4 audit -->
