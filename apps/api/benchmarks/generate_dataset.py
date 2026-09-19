"""
DocuMind AI — Benchmark Dataset & Ground Truth Generator.

Generates 20 diverse, realistic, non-sensitive documents across various formats,
sizes, and structures (invoices, NDAs, resumes, incident reports, technical specs,
financial statements, clinical protocols, whitepapers, research papers).
Also generates ground_truth_50.json containing 50 specific evaluation queries with
exact target document, expected answers, ground truth snippets, and categories.
"""

import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "ground_truth_50.json")

def create_pdf(filename: str, story: list):
    os.makedirs(DATASET_DIR, exist_ok=True)
    filepath = os.path.join(DATASET_DIR, filename)
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(story)
    return filepath

def generate_all_documents():
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h1_style = styles["Heading1"]
    h2_style = styles["Heading2"]
    body_style = styles["Normal"]
    body_style.fontSize = 10
    body_style.leading = 14

    docs_info = []

    # -------------------------------------------------------------
    # Doc 1: Invoice Q1 (Small, 1 page)
    # -------------------------------------------------------------
    s1 = [
        Paragraph("<b>INVOICE #INV-2026-8841</b>", title_style),
        Spacer(1, 15),
        Paragraph("<b>Billed To:</b> Acronis Cloud Solutions, 450 Enterprise Way, Austin, TX", body_style),
        Paragraph("<b>Vendor:</b> NovaGrid Infrastructure Inc., 100 Silicon Blvd, San Jose, CA", body_style),
        Paragraph("<b>Tax ID:</b> 94-3829104 | <b>Issue Date:</b> January 15, 2026 | <b>Due Date:</b> February 15, 2026", body_style),
        Paragraph("<b>Payment Terms:</b> Net 30 via ACH Wire Transfer (Routing: 121000358, Account: 994021482)", body_style),
        Spacer(1, 15),
    ]
    t1_data = [
        ["Line Item", "Description", "Quantity", "Unit Price", "Total"],
        ["SVC-01", "Dedicated GPU Cluster Slicing (A100-80GB)", "120 hrs", "$3.50", "$420.00"],
        ["SVC-02", "Vector Database Cloud Hosting (Qdrant Tier 2)", "1 month", "$650.00", "$650.00"],
        ["SVC-03", "Low-Latency Cold Storage Archive (50TB)", "50 TB", "$4.20", "$210.00"],
        ["SVC-04", "Enterprise SLA 24/7 SRE Support", "1 month", "$1,200.00", "$1,200.00"],
        ["", "", "", "<b>Subtotal</b>", "$2,480.00"],
        ["", "", "", "<b>Sales Tax (8.25%)</b>", "$204.60"],
        ["", "", "", "<b>Grand Total Due</b>", "<b>$2,684.60</b>"],
    ]
    t1 = Table(t1_data, colWidths=[60, 220, 60, 70, 70])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    s1.append(t1)
    s1.append(Spacer(1, 15))
    s1.append(Paragraph("<b>Note:</b> Late payments incur a 1.5% monthly compound penalty fee. Remit payments to payments@novagrid.io.", body_style))
    create_pdf("doc01_invoice_q1.pdf", s1)
    docs_info.append({"id": "doc01", "filename": "doc01_invoice_q1.pdf", "type": "invoice", "target_pages": 1})

    # -------------------------------------------------------------
    # Doc 2: NDA Agreement (Small, 2 pages)
    # -------------------------------------------------------------
    s2 = [
        Paragraph("<b>MUTUAL NON-DISCLOSURE AGREEMENT</b>", title_style),
        Spacer(1, 10),
        Paragraph("This Mutual Non-Disclosure Agreement ('Agreement') is entered into on March 4, 2026, by and between Apex Ventures LLC ('Disclosing Party') and Helix Dynamics Corp ('Receiving Party').", body_style),
        Spacer(1, 10),
        Paragraph("<b>1. Definition of Confidential Information</b>", h2_style),
        Paragraph("Confidential Information includes all non-public technical data, source code, trade secrets, financial models, customer rosters, and neural network weight checkpoints disclosed directly or indirectly.", body_style),
        Spacer(1, 10),
        Paragraph("<b>2. Standard of Care and Security Controls</b>", h2_style),
        Paragraph("The Receiving Party agrees to exercise at least a reasonable standard of care, maintaining AES-256 encryption at rest and TLS 1.3 in transit for all exchanged electronic documents.", body_style),
        PageBreak(),
        Paragraph("<b>3. Exclusions from Confidentiality</b>", h2_style),
        Paragraph("Obligations shall not apply to information that: (a) becomes publicly known through no breach of this Agreement; (b) is received from a third party without breach of duty; or (c) was independently developed without reference to the Disclosing Party's data.", body_style),
        Spacer(1, 10),
        Paragraph("<b>4. Term and Governing Jurisdiction</b>", h2_style),
        Paragraph("This Agreement remains in effect for a period of three (3) years from the effective date. This Agreement shall be governed strictly by the laws of the State of Delaware, without regard to conflict of law principles. Any dispute shall be resolved in New Castle County Chancery Court.", body_style),
        Spacer(1, 20),
        Paragraph("<b>Signatures:</b><br/>Apex Ventures LLC: Elena Vance, General Partner<br/>Helix Dynamics Corp: Marcus Brody, Chief Executive Officer", body_style),
    ]
    create_pdf("doc02_nda_agreement.pdf", s2)
    docs_info.append({"id": "doc02", "filename": "doc02_nda_agreement.pdf", "type": "nda", "target_pages": 2})

    # -------------------------------------------------------------
    # Doc 3: Executive Resume (Small, 2 pages)
    # -------------------------------------------------------------
    s3 = [
        Paragraph("<b>DR. SARAH CHEN — PRINCIPAL AI SYSTEMS ARCHITECT</b>", title_style),
        Paragraph("San Francisco, CA | sarah.chen.ai@example.com | github.com/sarahchen-ai", body_style),
        Spacer(1, 10),
        Paragraph("<b>Executive Summary</b>", h2_style),
        Paragraph("12+ years specializing in distributed systems, vector retrieval engines, and LLM inference optimization. Led architectures serving 500M+ daily embeddings with sub-15ms P99 retrieval latency.", body_style),
        Spacer(1, 10),
        Paragraph("<b>Core Technical Competencies</b>", h2_style),
        Paragraph("Languages: Python, Rust, C++, Go, TypeScript. Infrastructure: Qdrant, Milvus, Kubernetes, Docker, Ray, Triton Inference Server, vLLM, TensorRT-LLM, CUDA 12.x.", body_style),
        Spacer(1, 10),
        Paragraph("<b>Professional Experience</b>", h2_style),
        Paragraph("<b>VP of AI Infrastructure — HyperScale Labs (2022–Present)</b>", h2_style),
        Paragraph("• Architected multi-region hybrid semantic search engine indexing 800M vectors across 64 nodes, achieving 99.995% uptime.<br/>• Cut LLM token serving latency by 42% through speculative decoding and FlashAttention-3 integration.<br/>• Reduced annual cloud expenditure by $1.8M by designing an automated dynamic context pruning heuristic.", body_style),
        PageBreak(),
        Paragraph("<b>Lead Machine Learning Engineer — Cognitive Dynamics (2018–2022)</b>", h2_style),
        Paragraph("• Designed distributed document chunking and embedding pipelines processing 12TB of unstructured PDF datasets per day.<br/>• Implemented hierarchical HNSW graph indexing algorithms reducing RAM footprint by 35% without recall degradation.<br/>• Mentored an engineering group of 18 machine learning and data infrastructure engineers.", body_style),
        Spacer(1, 10),
        Paragraph("<b>Education & Patents</b>", h2_style),
        Paragraph("• <b>Ph.D. in Computer Science</b>, Stanford University, 2018. Dissertation: 'Accelerated Approximate Nearest Neighbor Search in High-Dimensional Manifolds'.<br/>• <b>B.S. in Electrical Engineering & CS</b>, UC Berkeley, 2014. Summa Cum Laude.<br/>• <b>US Patent #11,489,203</b>: 'Adaptive Vector Quantization for High-Throughput Approximate Nearest Neighbor Lookups'.", body_style),
    ]
    create_pdf("doc03_executive_resume.pdf", s3)
    docs_info.append({"id": "doc03", "filename": "doc03_executive_resume.pdf", "type": "resume", "target_pages": 2})

    # -------------------------------------------------------------
    # Doc 4: Security Incident Report (Small, 2 pages)
    # -------------------------------------------------------------
    s4 = [
        Paragraph("<b>POSTMORTEM: INCIDENT #SEC-2026-0419</b>", title_style),
        Spacer(1, 10),
        Paragraph("<b>Incident Severity:</b> P1 (High) | <b>Lead Responder:</b> Jason Morales, Staff Security Engineer", body_style),
        Paragraph("<b>Date of Occurrence:</b> February 12, 2026 03:14 UTC | <b>Resolved:</b> February 12, 2026 05:42 UTC (Total Duration: 2h 28m)", body_style),
        Spacer(1, 10),
        Paragraph("<b>1. Incident Summary</b>", h2_style),
        Paragraph("At 03:14 UTC, our automated canary alerts flagged anomalous spikes in egress network bandwidth originating from worker node worker-gpu-08. Analysis revealed an unauthorized external DNS exfiltration attempt caused by a compromised dependency package 'pdf-formatter-core' v1.2.8.", body_style),
        Spacer(1, 10),
        Paragraph("<b>2. Root Cause Analysis</b>", h2_style),
        Paragraph("A typosquatted malicious dependency was inadvertently merged during an unpinned lockfile update. The malicious payload attempted to transmit environment variable secrets via base64 DNS tunneling to an external command-and-control server (c2.shadow-network.org).", body_style),
        PageBreak(),
        Paragraph("<b>3. Impact Assessment</b>", h2_style),
        Paragraph("• Vector Store Data: No breach. Vector endpoints were isolated behind private VPC subnets.<br/>• Customer Documents: 0 documents accessed. Egress firewalls blocked 99.4% of outbound requests.<br/>• Credentials Affected: A staging Supabase service key was rotated immediately as a defensive measure.", body_style),
        Spacer(1, 10),
        Paragraph("<b>4. Corrective & Preventative Actions</b>", h2_style),
        Paragraph("1. Implemented strict hash-pinned software bills of materials (SBOM) across all CI/CD pipelines.<br/>2. Deployed eBPF-based runtime syscall enforcement to terminate unexpected socket connections instantaneously.<br/>3. Mandated multi-party code reviews for any dependency version alterations in requirements.txt.", body_style),
    ]
    create_pdf("doc04_security_incident_report.pdf", s4)
    docs_info.append({"id": "doc04", "filename": "doc04_security_incident_report.pdf", "type": "postmortem", "target_pages": 2})

    # -------------------------------------------------------------
    # Doc 5: Product Roadmap Memo (Small, 2 pages)
    # -------------------------------------------------------------
    s5 = [
        Paragraph("<b>MEMORANDUM: PRODUCT ROADMAP H2 2026</b>", title_style),
        Spacer(1, 10),
        Paragraph("<b>To:</b> Executive Leadership Committee | <b>From:</b> VP of Product, Maya Lin", body_style),
        Paragraph("<b>Subject:</b> Strategic AI Platform Milestones & Enterprise Commitments | <b>Date:</b> May 18, 2026", body_style),
        Spacer(1, 10),
        Paragraph("<b>Executive Summary</b>", h2_style),
        Paragraph("In H2 2026, DocuMind AI will expand from a single-tenant document search engine into a collaborative multimodal intelligence workbench. Our top strategic goal is reaching $4.5M ARR by Q4 2026 while maintaining 99.9% uptime SLA.", body_style),
        Spacer(1, 10),
        Paragraph("<b>Key Deliverables & Target Quarters</b>", h2_style),
        Paragraph("• <b>Q3 Milestone (Release v2.0):</b> Deep Hybrid Retrieval combining BM25 lexical keyword matching with dense vector representations from Gemini-Embedding-2.<br/>• <b>Q3 Milestone (Release v2.1):</b> Real-time collaborative multi-user chat sessions with granular cursor synchronization.<br/>• <b>Q4 Milestone (Release v3.0):</b> Automated cross-document synthesis generating 15-page comparative executive briefings in under 30 seconds.", body_style),
        PageBreak(),
        Paragraph("<b>Resource Allocations & Budgeting</b>", h2_style),
        Paragraph("Total approved capital allocation for H2 infrastructure is $680,000, broken down as follows:", body_style),
        Spacer(1, 10),
    ]
    t5_data = [
        ["Budget Category", "Allocation ($)", "Primary Vendor", "Expected Outcome"],
        ["GPU Compute (Inference)", "$320,000", "Lambda Labs / RunPod", "Support 50k concurrent requests"],
        ["Managed Vector Storage", "$140,000", "Qdrant Cloud Enterprise", "Host 2.5 billion document vectors"],
        ["Security & Pen-testing", "$90,000", "Bishop Fox", "SOC2 Type II recertification"],
        ["Data Engineering Pipeline", "$130,000", "Internal Tooling & AWS", "Sub-2s ingestion on 100-page PDFs"],
    ]
    t5 = Table(t5_data, colWidths=[120, 90, 130, 160])
    t5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    s5.append(t5)
    s5.append(Spacer(1, 15))
    s5.append(Paragraph("<b>Target Exit Velocity:</b> Sustained Gross Margin above 78% by end of December 2026.", body_style))
    create_pdf("doc05_product_roadmap_memo.pdf", s5)
    docs_info.append({"id": "doc05", "filename": "doc05_product_roadmap_memo.pdf", "type": "memo", "target_pages": 2})

    # -------------------------------------------------------------
    # Doc 6: Software Architecture Spec (Medium, 4 pages)
    # -------------------------------------------------------------
    s6 = [
        Paragraph("<b>TECHNICAL SPECIFICATION: DISTRIBUTED CACHING LAYER v4.2</b>", title_style),
        Paragraph("Author: Principal Infrastructure Architect | Status: Approved for Production", body_style),
        Spacer(1, 10),
        Paragraph("<b>1. Purpose & Architectural Overview</b>", h1_style),
        Paragraph("This document specifies the multi-tier distributed caching architecture designed to eliminate redundant LLM embedding computations and reduce database read queries on repetitive semantic queries. Target latency is sub-5ms for cache hits.", body_style),
        Paragraph("The cache employs a two-layer hierarchy: Layer 1 is in-memory local LRU cache (Python cachetools) with 5,000 item capacity. Layer 2 is a distributed Redis 7.2 cluster operating with cluster mode enabled and Raft-based consensus failover.", body_style),
        Spacer(1, 10),
        Paragraph("<b>2. Cache Key Formulation & Eviction Policies</b>", h1_style),
        Paragraph("Cache keys are computed using SHA-256 over normalized text payloads and tenant UUIDs. The schema follows: <code>documind:tenant:{user_id}:hash:{sha256}</code>. TTL for document embeddings is strictly 14 days, whereas semantic query cache entries expire after 4 hours.", body_style),
        PageBreak(),
        Paragraph("<b>3. Circuit Breaker Parameters & Resilience</b>", h1_style),
        Paragraph("To shield upstream vector databases and relational databases during thundering herds, a Resilience4j-inspired sliding-window circuit breaker is enforced. The breaker transitions to OPEN if failure rates exceed 25% over a 60-second window with a minimum call volume of 40 requests.", body_style),
        Paragraph("When in OPEN state, the application falls back immediately to degraded degraded local lexical search without raising HTTP 500 exceptions to end users.", body_style),
        Spacer(1, 10),
        Paragraph("<b>4. Performance Benchmark Targets</b>", h1_style),
        Paragraph("• Cache Hit Ratio target: >= 68% across all production RAG workloads.<br/>• Read latency: P50 < 1.2ms, P95 < 3.8ms, P99 < 8.5ms.<br/>• Maximum allowable cluster memory utilization: 75% of available 64GB RAM.", body_style),
        PageBreak(),
        Paragraph("<b>5. Observability & Prometheus Metrics</b>", h1_style),
        Paragraph("All cache interactions expose Prometheus metrics on port 9090. Metric names:<br/>• <code>documind_cache_hits_total{tier='redis'}</code><br/>• <code>documind_cache_misses_total{tier='redis'}</code><br/>• <code>documind_cache_latency_seconds_bucket</code><br/>Alert threshold: Page on-call if cache hit ratio drops below 40% for more than 15 consecutive minutes.", body_style),
        Spacer(1, 10),
        Paragraph("<b>6. Disaster Recovery & Backup Plan</b>", h1_style),
        Paragraph("Redis RDB snapshots are taken every 3 hours and pushed to encrypted AWS S3 buckets in region us-east-1. Append-Only File (AOF) with <code>fsync everysec</code> is enabled to limit potential data loss to under 1 second of cache keys.", body_style),
        PageBreak(),
        Paragraph("<b>7. Security & Encryption Standards</b>", h1_style),
        Paragraph("All Redis connections require mTLS with client certificate verification. Passwords must have at least 64 bytes of cryptographically random entropy loaded from HashiCorp Vault. In-transit encryption uses TLS 1.3 with AES-GCM cipher suites.", body_style),
        Paragraph("Signed-off by Security Governance Board on January 22, 2026.", body_style),
    ]
    create_pdf("doc06_software_spec.pdf", s6)
    docs_info.append({"id": "doc06", "filename": "doc06_software_spec.pdf", "type": "spec", "target_pages": 4})

    # -------------------------------------------------------------
    # Doc 7: Quarterly Financial Report (Medium, 5 pages)
    # -------------------------------------------------------------
    s7 = [
        Paragraph("<b>NEXUS TECHNOLOGIES Q4 2025 FINANCIAL AUDIT REPORT</b>", title_style),
        Paragraph("Audited by PriceWaterhouseGlobal LLP | Published: February 2026", body_style),
        Spacer(1, 10),
        Paragraph("<b>1. Consolidated Revenue Summary</b>", h1_style),
        Paragraph("Nexus Technologies demonstrated exceptional annual growth in fiscal year 2025. Total annual revenue reached $142.8M, representing a 34.2% year-over-year expansion driven primarily by the Enterprise AI Software Division.", body_style),
        Spacer(1, 10),
    ]
    t7_data = [
        ["Fiscal Quarter", "Cloud Subscription ($M)", "Professional Services ($M)", "Licensing ($M)", "Total Revenue ($M)"],
        ["Q1 2025", "$24.2M", "$4.1M", "$2.8M", "$31.1M"],
        ["Q2 2025", "$27.5M", "$3.9M", "$3.1M", "$34.5M"],
        ["Q3 2025", "$30.8M", "$4.4M", "$3.3M", "$38.5M"],
        ["Q4 2025", "$32.4M", "$4.2M", "$2.1M", "$38.7M"],
        ["Full Year 2025", "$114.9M", "$16.6M", "$11.3M", "$142.8M"],
    ]
    t7 = Table(t7_data, colWidths=[90, 110, 110, 80, 90])
    t7.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    s7.append(t7)
    s7.append(PageBreak())
    s7.append(Paragraph("<b>2. Operational Expenses Breakdown</b>", h1_style))
    s7.append(Paragraph("Operating expenses totaled $98.4M for the full year 2025. Research and Development (R&D) represented the largest operational expenditure at $48.2M (49.0% of total OPEX), emphasizing our ongoing commitment to frontier AI model fine-tuning and inference infrastructure.", body_style))
    s7.append(Spacer(1, 10))
    s7.append(Paragraph("Sales and Marketing (S&M) amounted to $32.1M, reflecting expanded customer acquisition in Europe and the APAC region. General and Administrative (G&A) expenses were kept lean at $18.1M.", body_style))
    s7.append(PageBreak())
    s7.append(Paragraph("<b>3. EBITDA & Operating Margins</b>", h1_style))
    s7.append(Paragraph("Adjusted EBITDA for Q4 2025 stood at $11.4M (29.5% EBITDA margin), compared to $7.8M in Q4 2024. Full-year free cash flow was $26.8M, representing a cash conversion rate of 72.4% relative to net operating income.", body_style))
    s7.append(PageBreak())
    s7.append(Paragraph("<b>4. Balance Sheet & Liquidity Position</b>", h1_style))
    s7.append(Paragraph("As of December 31, 2025, Nexus Technologies held $68.4M in cash and cash equivalents, and $24.0M in short-term US Treasury bills. Total liabilities stood at $31.2M, with zero long-term funded debt obligations.", body_style))
    s7.append(PageBreak())
    s7.append(Paragraph("<b>5. FY 2026 Guidance & Risk Factors</b>", h1_style))
    s7.append(Paragraph("Management projects FY 2026 total revenue between $185M and $195M, driven by rapid customer migration to automated generative document workflows. Primary risk factors include GPU allocation supply constraints and potential regulatory scrutiny under the EU AI Act.", body_style))
    create_pdf("doc07_quarterly_financial_report.pdf", s7)
    docs_info.append({"id": "doc07", "filename": "doc07_quarterly_financial_report.pdf", "type": "financial", "target_pages": 5})

    # -------------------------------------------------------------
    # Doc 8: HR Employee Handbook (Medium, 6 pages)
    # -------------------------------------------------------------
    s8 = [
        Paragraph("<b>VORTEX GLOBAL EMPLOYEE HANDBOOK 2026</b>", title_style),
        Spacer(1, 10),
        Paragraph("<b>Welcome to Vortex Global</b>", h1_style),
        Paragraph("This handbook establishes the core operational guidelines, conduct standards, and employee benefits for all full-time and part-time staff members worldwide.", body_style),
        PageBreak(),
        Paragraph("<b>Section 1: Working Hours & Remote Work Guidelines</b>", h1_style),
        Paragraph("Core collaboration hours are 10:00 AM to 3:00 PM in each employee's local timezone. Vortex operates on an async-first philosophy. Remote employees receive an initial $1,500 home-office setup stipend and a recurring $150 monthly broadband and utility reimbursement.", body_style),
        PageBreak(),
        Paragraph("<b>Section 2: Paid Time Off (PTO) & Leave Entitlements</b>", h1_style),
        Paragraph("Full-time employees receive 25 days of annual paid vacation leave, 10 days of paid sick leave, and 12 company-observed national holidays. Vortex mandates a minimum annual vacation usage of 15 days to guarantee mental wellness and prevent employee burnout.", body_style),
        Paragraph("Parental Leave: Primary and secondary caregivers are entitled to 16 weeks of fully paid parental leave within the first 12 months following birth or adoption.", body_style),
        PageBreak(),
        Paragraph("<b>Section 3: Health Insurance, Wellness & Retirement Plans</b>", h1_style),
        Paragraph("Vortex covers 100% of medical, dental, and vision insurance premiums for all employees and 75% for dependents. We offer a 401(k) retirement match of 100% on the first 5% of salary contributed, vesting immediately on day one of employment.", body_style),
        PageBreak(),
        Paragraph("<b>Section 4: Professional Development & Educational Grants</b>", h1_style),
        Paragraph("Each team member is allotted an annual continuous learning grant of $3,500. This fund can be applied toward technical certifications, academic conferences, textbooks, and graduate course tuition with prior manager sign-off.", body_style),
        PageBreak(),
        Paragraph("<b>Section 5: Code of Business Ethics & Anti-Harassment Policy</b>", h1_style),
        Paragraph("Vortex enforces zero tolerance for discrimination, sexual harassment, or retaliation. All formal grievances can be reported anonymously via the 24/7 Ethics Hotline at 1-800-555-0199 or via ethics@vortexglobal.com.", body_style),
    ]
    create_pdf("doc08_hr_employee_handbook.pdf", s8)
    docs_info.append({"id": "doc08", "filename": "doc08_hr_employee_handbook.pdf", "type": "handbook", "target_pages": 6})

    # -------------------------------------------------------------
    # Doc 9: Clinical Trial Protocol (Medium, 6 pages)
    # -------------------------------------------------------------
    s9 = [
        Paragraph("<b>CLINICAL TRIAL PROTOCOL: INVESTIGATIONAL COMPOUND VX-709</b>", title_style),
        Paragraph("Protocol ID: NCT05829104 | Sponsor: BioGenex Therapeutics | Phase: IIb", body_style),
        Spacer(1, 10),
        Paragraph("<b>1. Study Synopsis & Objectives</b>", h1_style),
        Paragraph("This Phase IIb multicenter, randomized, double-blind, placebo-controlled study evaluates the therapeutic efficacy, safety, and pharmacokinetic profile of oral VX-709 in adult patients with moderate-to-severe ulcerative colitis.", body_style),
        PageBreak(),
        Paragraph("<b>2. Patient Inclusion Criteria</b>", h1_style),
        Paragraph("• Age 18 to 70 years at the time of signing informed consent.<br/>• Confirmed diagnosis of ulcerative colitis for >= 6 months established by clinical and endoscopic evidence.<br/>• Total Mayo score of 6 to 12 points, including an endoscopic subscore of >= 2.", body_style),
        PageBreak(),
        Paragraph("<b>3. Patient Exclusion Criteria</b>", h1_style),
        Paragraph("• Prior exposure to JAK inhibitors or anti-TNF biologics within 8 weeks of randomization.<br/>• History of severe cardiovascular events, deep vein thrombosis, or pulmonary embolism within 12 months.<br/>• Absolute neutrophil count (ANC) < 1,500 cells/uL or serum creatinine > 1.8 mg/dL.", body_style),
        PageBreak(),
        Paragraph("<b>4. Dosage Regimens & Administration Schedule</b>", h1_style),
        Paragraph("Subjects are randomized 1:1:1 into three treatment arms: (Arm A) VX-709 15mg once daily; (Arm B) VX-709 30mg once daily; (Arm C) Matched Placebo once daily. Study medication must be taken in the morning with 240mL of water with or without food.", body_style),
        PageBreak(),
        Paragraph("<b>5. Primary & Secondary Endpoints</b>", h1_style),
        Paragraph("Primary Endpoint: Proportion of patients achieving clinical remission (Mayo score <= 2 with no individual subscore > 1) at Week 12.<br/>Secondary Endpoints: Endoscopic mucosal healing at Week 12 and Week 24; change from baseline in fecal calprotectin levels at Week 4, 8, and 12.", body_style),
        PageBreak(),
        Paragraph("<b>6. Adverse Event Reporting & Data Safety Monitoring</b>", h1_style),
        Paragraph("All Serious Adverse Events (SAEs) must be transmitted to the Medical Monitor within 24 hours of site awareness. An independent Data Safety Monitoring Board (DSMB) reviews unblinded safety data every 6 weeks.", body_style),
    ]
    create_pdf("doc09_clinical_trial_protocol.pdf", s9)
    docs_info.append({"id": "doc09", "filename": "doc09_clinical_trial_protocol.pdf", "type": "clinical", "target_pages": 6})

    # -------------------------------------------------------------
    # Doc 10: Cloud Migration Guide (Medium, 7 pages)
    # -------------------------------------------------------------
    s10 = []
    for p in range(1, 8):
        s10.append(Paragraph(f"<b>ENTERPRISE AWS CLOUD MIGRATION PLAYBOOK — CHAPTER {p}</b>", title_style if p==1 else h1_style))
        if p == 1:
            s10.append(Paragraph("<b>Executive Strategy: 6R Migration Framework</b><br/>Our enterprise cloud transition adopts the AWS 6R framework: Rehost, Replatform, Repurchase, Refactor, Retire, and Retain. Phase 1 targets the complete migration of 42 core microservices to Amazon EKS within 180 days.", body_style))
        elif p == 2:
            s10.append(Paragraph("<b>Networking Architecture & VPC Peering</b><br/>The multi-account structure features dedicated Ingress, Egress, Shared Services, and Workload VPCs connected via AWS Transit Gateway. Transit Gateway encryption uses AWS Key Management Service (KMS) customer-managed keys.", body_style))
        elif p == 3:
            s10.append(Paragraph("<b>Kubernetes EKS Cluster Sizing & Node Pools</b><br/>Production clusters utilize Karpenter for dynamic node provisioning. The base pool runs 12 m6i.4xlarge EC2 instances spanning 3 Availability Zones (us-east-1a, 1b, 1c) with pod anti-affinity guarantees.", body_style))
        elif p == 4:
            s10.append(Paragraph("<b>Database Migration via AWS DMS</b><br/>PostgreSQL 14 databases (totaling 8.4TB) are synchronized to Amazon Aurora PostgreSQL using AWS Database Migration Service (DMS) with continuous Change Data Capture (CDC). Target cutover downtime window: < 15 minutes.", body_style))
        elif p == 5:
            s10.append(Paragraph("<b>Security Compliance, IAM Roles & KMS</b><br/>IAM Roles for Service Accounts (IRSA) replace static AWS credentials in containers. All S3 buckets enforce Object Lock in compliance mode and default SSE-KMS encryption.", body_style))
        elif p == 6:
            s10.append(Paragraph("<b>Disaster Recovery RTO and RPO Guarantees</b><br/>Multi-region active-passive failover between us-east-1 and us-west-2 ensures a Recovery Time Objective (RTO) under 30 minutes and a Recovery Point Objective (RPO) under 5 minutes for tier-1 workloads.", body_style))
        elif p == 7:
            s10.append(Paragraph("<b>Cost Optimization & Spot Instance Policies</b><br/>Non-production test environments run exclusively on EC2 Spot Instances, reducing compute costs by 68%. All unused resources are automatically scaled to zero outside business hours using Kubernetes Keda cron triggers.", body_style))
        if p < 7:
            s10.append(PageBreak())
    create_pdf("doc10_cloud_migration_guide.pdf", s10)
    docs_info.append({"id": "doc10", "filename": "doc10_cloud_migration_guide.pdf", "type": "technical", "target_pages": 7})

    # -------------------------------------------------------------
    # Doc 11: Data Privacy GDPR Policy (Medium, 8 pages)
    # -------------------------------------------------------------
    s11 = []
    gdpr_sections = [
        ("Article 1: Scope & Data Controller Details", "DocuMind Corp operates as the Data Controller under Regulation (EU) 2016/679. Our nominated Data Protection Officer (DPO) can be reached at dpo@documind.eu or Rue de la Loi 200, 1040 Brussels, Belgium."),
        ("Article 2: Lawful Basis for Processing", "Processing of document metadata is conducted under Article 6(1)(b) necessary for performance of a contract, and Article 6(1)(f) legitimate business interest for security telemetry."),
        ("Article 3: Data Subject Access Requests (DSAR)", "Data subjects retain the right to obtain confirmation, rectification, or erasure (Right to be Forgotten). All verified DSAR requests must be fulfilled within thirty (30) calendar days."),
        ("Article 4: Cross-Border Data Transfers", "Transfers of personal data outside the European Economic Area (EEA) rely exclusively on the European Commission's Standard Contractual Clauses (SCCs) combined with supplemental technical encryption safeguards."),
        ("Article 5: Retention & Cryptographic Erasure", "Document contents uploaded for ad-hoc semantic search are retained for the duration of the active user session plus 7 days, after which cryptographic zeroization occurs."),
        ("Article 6: Breach Notification Timeline", "In accordance with Article 33, any personal data breach causing high risk to rights and freedoms will be notified to the relevant Supervisory Authority within 72 hours of becoming aware."),
        ("Article 7: Third-Party Sub-Processors", "Current authorized sub-processors include: Supabase Inc. (Database Hosting), Qdrant Cloud Solutions (Vector Indexing), and Google Cloud Platform (Embedding Inference)."),
        ("Article 8: Fines & Regulatory Oversight", "Infringements of core provisions are subject to administrative fines up to €20,000,000 or 4% of total worldwide annual turnover of the preceding financial year, whichever is higher."),
    ]
    for idx, (head, text) in enumerate(gdpr_sections, 1):
        s11.append(Paragraph(f"<b>GDPR COMPLIANCE & PRIVACY CHARTER — {head}</b>", title_style if idx==1 else h1_style))
        s11.append(Spacer(1, 10))
        s11.append(Paragraph(text, body_style))
        if idx < len(gdpr_sections):
            s11.append(PageBreak())
    create_pdf("doc11_data_privacy_gdpr_policy.pdf", s11)
    docs_info.append({"id": "doc11", "filename": "doc11_data_privacy_gdpr_policy.pdf", "type": "legal", "target_pages": 8})

    # -------------------------------------------------------------
    # Doc 12: API Developer Guide (Medium, 8 pages)
    # -------------------------------------------------------------
    s12 = []
    api_chapters = [
        ("API Architecture & Base URLs", "The DocuMind API follows RESTful architectural principles. Production endpoints are accessible at https://api.documind.ai/v1. All API payloads use UTF-8 JSON."),
        ("Authentication & API Keys", "All requests require a Bearer token passed in the Authorization header: 'Authorization: Bearer <API_KEY>'. Keys start with prefix 'dm_live_' for production and 'dm_test_' for sandbox environments."),
        ("Rate Limiting & Headers", "Standard Tier rate limits allow 120 requests per minute and 10,000 requests per day. Response headers include X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset."),
        ("Document Ingestion Endpoints", "POST /v1/documents/signed-url requests pre-signed storage URLs. POST /v1/documents/register submits document metadata for asynchronous background ingestion."),
        ("Semantic Search & Retrieval", "POST /v1/search accepts query string, top_k integer (default 5, max 50), and score_threshold float (0.0 to 1.0). Returns list of chunk objects with similarity scores."),
        ("Streaming Chat & SSE Protocol", "POST /v1/chat/stream utilizes Server-Sent Events (SSE). Chunks are emitted in format 'data: {\"content\": \"...\", \"provider\": \"...\"}' terminating with '[DONE]'."),
        ("Error Handling & Status Codes", "The API returns standard RFC 7807 problem details. Status 400 = Bad Request, 401 = Unauthorized, 404 = Not Found, 422 = Validation Error, 429 = Rate Limit Exceeded, 503 = Service Unavailable."),
        ("Webhooks & Event Subscriptions", "Subscribers receive HMAC-SHA256 signed event notifications for events: 'document.processed', 'document.failed', and 'model.fallback_activated'."),
    ]
    for idx, (head, text) in enumerate(api_chapters, 1):
        s12.append(Paragraph(f"<b>DEVELOPER REFERENCE MANUAL — {head}</b>", title_style if idx==1 else h1_style))
        s12.append(Spacer(1, 10))
        s12.append(Paragraph(text, body_style))
        if idx < len(api_chapters):
            s12.append(PageBreak())
    create_pdf("doc12_api_developer_guide.pdf", s12)
    docs_info.append({"id": "doc12", "filename": "doc12_api_developer_guide.pdf", "type": "api", "target_pages": 8})

    # -------------------------------------------------------------
    # Doc 13: Cybersecurity Framework Audit (Medium, 10 pages)
    # -------------------------------------------------------------
    s13 = []
    for p in range(1, 11):
        s13.append(Paragraph(f"<b>SOC 2 TYPE II SECURITY AUDIT REPORT — SECTION {p}</b>", title_style if p==1 else h1_style))
        s13.append(Spacer(1, 10))
        s13.append(Paragraph(f"Trust Services Criteria Evaluation for Section {p}: The audit examined controls across Security, Availability, and Confidentiality. For control CC{p}.1, independent auditors confirmed continuous automated configuration tracking and zero critical non-conformities across all production assets. Penetration test results yielded zero high-severity findings during the testing window from October 1 to December 31, 2025.", body_style))
        if p < 10:
            s13.append(PageBreak())
    create_pdf("doc13_cybersecurity_framework_audit.pdf", s13)
    docs_info.append({"id": "doc13", "filename": "doc13_cybersecurity_framework_audit.pdf", "type": "security", "target_pages": 10})

    # -------------------------------------------------------------
    # Doc 14: AI Ethics Whitepaper (Large, 15 pages)
    # -------------------------------------------------------------
    s14 = []
    for p in range(1, 16):
        s14.append(Paragraph(f"<b>ETHICAL GOVERNANCE OF AUTONOMOUS REASONING SYSTEMS — PART {p}</b>", title_style if p==1 else h1_style))
        s14.append(Spacer(1, 10))
        s14.append(Paragraph(f"Analysis of fairness, accountability, transparency, and safety mechanisms in generative reasoning architectures (Section {p}). High-capacity language models demonstrate emergent reasoning behavior that demands verifiable citation mechanisms and strict provenance tracking. Measuring hallucination entropy via conformal prediction sets provides mathematical guarantees against fabricated citations in clinical and legal domains.", body_style))
        if p < 15:
            s14.append(PageBreak())
    create_pdf("doc14_ai_ethics_whitepaper.pdf", s14)
    docs_info.append({"id": "doc14", "filename": "doc14_ai_ethics_whitepaper.pdf", "type": "whitepaper", "target_pages": 15})

    # -------------------------------------------------------------
    # Doc 15: Distributed Consensus Research (Large, 16 pages)
    # -------------------------------------------------------------
    s15 = []
    for p in range(1, 17):
        s15.append(Paragraph(f"<b>FORMAL VERIFICATION OF DISTRIBUTED CONSENSUS PROTOCOLS — CHAPTER {p}</b>", title_style if p==1 else h1_style))
        s15.append(Spacer(1, 10))
        s15.append(Paragraph(f"Theoretical foundations and empirical evaluation of Raft vs Multi-Paxos in geo-distributed partitions (Section {p}). By decoupling log replication from leader election through pipelined append entries, latency drops by 38% across cross-continental WAN links. Quorum intersections guarantee linearizability under asynchronous network failure models where f out of 2f+1 nodes fail.", body_style))
        if p < 16:
            s15.append(PageBreak())
    create_pdf("doc15_distributed_consensus_research.pdf", s15)
    docs_info.append({"id": "doc15", "filename": "doc15_distributed_consensus_research.pdf", "type": "research", "target_pages": 16})

    # -------------------------------------------------------------
    # Doc 16: Climate Sustainability Report (Large, 18 pages)
    # -------------------------------------------------------------
    s16 = []
    for p in range(1, 19):
        s16.append(Paragraph(f"<b>GLOBAL SUSTAINABILITY & DECARBONIZATION ASSESSMENT 2026 — VOL {p}</b>", title_style if p==1 else h1_style))
        s16.append(Spacer(1, 10))
        s16.append(Paragraph(f"Detailed audit of Scope 1, Scope 2, and Scope 3 greenhouse gas emissions across data center supply chains (Module {p}). By transitioning AI inference workloads to geothermal and wind-backed regions, carbon intensity was reduced from 420g CO2e/kWh to 48g CO2e/kWh. Water usage effectiveness (WUE) dropped to 0.18 liters per kilowatt-hour through closed-loop liquid dielectric immersion cooling.", body_style))
        if p < 18:
            s16.append(PageBreak())
    create_pdf("doc16_climate_sustainability_report.pdf", s16)
    docs_info.append({"id": "doc16", "filename": "doc16_climate_sustainability_report.pdf", "type": "report", "target_pages": 18})

    # -------------------------------------------------------------
    # Doc 17: Enterprise RFP Proposal (Large, 20 pages)
    # -------------------------------------------------------------
    s17 = []
    for p in range(1, 21):
        s17.append(Paragraph(f"<b>ENTERPRISE PLATFORM PROPOSAL FOR GLOBAL BANK CORP — SECTION {p}</b>", title_style if p==1 else h1_style))
        s17.append(Spacer(1, 10))
        s17.append(Paragraph(f"Technical architecture response, security SLA guarantees, and multi-tenant isolation specifications (Section {p}). DocuMind AI guarantees 99.99% service availability with dedicated VPC peering, private vector clusters in Qdrant, and zero data retention for model training. Tier 1 support response times are under 15 minutes with 24/7 dedicated telephone routing.", body_style))
        if p < 20:
            s17.append(PageBreak())
    create_pdf("doc17_enterprise_rfp_proposal.pdf", s17)
    docs_info.append({"id": "doc17", "filename": "doc17_enterprise_rfp_proposal.pdf", "type": "proposal", "target_pages": 20})

    # -------------------------------------------------------------
    # Doc 18: Pharmacokinetics Journal (Large, 22 pages)
    # -------------------------------------------------------------
    s18 = []
    for p in range(1, 23):
        s18.append(Paragraph(f"<b>JOURNAL OF CLINICAL PHARMACOKINETICS — MONOGRAPH {p}</b>", title_style if p==1 else h1_style))
        s18.append(Spacer(1, 10))
        s18.append(Paragraph(f"Pharmacokinetic and pharmacodynamic characterization of novel small-molecule kinase inhibitors (Section {p}). The mean elimination half-life (t1/2) was 14.8 hours, with an apparent volume of distribution (Vd) of 210 liters. Renal excretion accounted for less than 8% of total drug clearance, indicating predominant hepatic metabolism via cytochrome P450 3A4 (CYP3A4) enzyme pathways.", body_style))
        if p < 22:
            s18.append(PageBreak())
    create_pdf("doc18_pharmacokinetics_journal.pdf", s18)
    docs_info.append({"id": "doc18", "filename": "doc18_pharmacokinetics_journal.pdf", "type": "journal", "target_pages": 22})

    # -------------------------------------------------------------
    # Doc 19: Semiconductor Supply Chain (Large, 25 pages)
    # -------------------------------------------------------------
    s19 = []
    for p in range(1, 26):
        s19.append(Paragraph(f"<b>GLOBAL SEMICONDUCTOR LITHOGRAPHY & FAB CAPACITY OUTLOOK — CH {p}</b>", title_style if p==1 else h1_style))
        s19.append(Spacer(1, 10))
        s19.append(Paragraph(f"In-depth market dynamics and wafer fab equipment lead times for sub-2nm High-NA Extreme Ultraviolet (EUV) photolithography scanners (Section {p}). Lead times for high-numerical-aperture optical mirrors exceed 24 months, with global silicon wafer fabrication operating at 94.2% nominal utilization across Taiwan, Japan, and the United States.", body_style))
        if p < 25:
            s19.append(PageBreak())
    create_pdf("doc19_semiconductor_supply_chain.pdf", s19)
    docs_info.append({"id": "doc19", "filename": "doc19_semiconductor_supply_chain.pdf", "type": "industry_report", "target_pages": 25})

    # -------------------------------------------------------------
    # Doc 20: Global Macroeconomic Outlook (Large, 30 pages)
    # -------------------------------------------------------------
    s20 = []
    for p in range(1, 31):
        s20.append(Paragraph(f"<b>WORLD MACROECONOMIC STABILITY REPORT — VOLUME {p}</b>", title_style if p==1 else h1_style))
        s20.append(Spacer(1, 10))
        s20.append(Paragraph(f"International monetary policy trajectory, debt-to-GDP ratios, sovereign bond yields, and commodity price shock resilience across 48 advanced and emerging economies (Section {p}). Central banks navigate disinflationary forces while maintaining terminal policy rates at 3.75%, balancing structural labor productivity shifts against aging demographic head-winds.", body_style))
        if p < 30:
            s20.append(PageBreak())
    create_pdf("doc20_global_macroeconomic_outlook.pdf", s20)
    docs_info.append({"id": "doc20", "filename": "doc20_global_macroeconomic_outlook.pdf", "type": "macro_report", "target_pages": 30})

    # Now create the 50 ground truth queries
    queries = [
        # --- Doc 01 Invoices (Factual / Table) ---
        {"id": "q01", "doc_id": "doc01", "category": "factual", "difficulty": "easy",
         "query": "What is the invoice number and issue date for the Acronis invoice?",
         "ground_truth_answer": "Invoice #INV-2026-8841 was issued on January 15, 2026.",
         "key_snippets": ["INV-2026-8841", "January 15, 2026"]},
        {"id": "q02", "doc_id": "doc01", "category": "table", "difficulty": "medium",
         "query": "What was the unit price and total cost for the dedicated GPU cluster slicing?",
         "ground_truth_answer": "The unit price was $3.50 per hour for 120 hours, totaling $420.00.",
         "key_snippets": ["$3.50", "$420.00", "Dedicated GPU Cluster Slicing"]},
        {"id": "q03", "doc_id": "doc01", "category": "table", "difficulty": "easy",
         "query": "What is the grand total due on invoice INV-2026-8841?",
         "ground_truth_answer": "The grand total due is $2,684.60, including $204.60 in sales tax.",
         "key_snippets": ["$2,684.60", "$204.60"]},
        {"id": "q04", "doc_id": "doc01", "category": "factual", "difficulty": "easy",
         "query": "What is the late payment penalty fee specified in the invoice?",
         "ground_truth_answer": "Late payments incur a 1.5% monthly compound penalty fee.",
         "key_snippets": ["1.5%", "monthly compound penalty"]},

        # --- Doc 02 NDA Agreement ---
        {"id": "q05", "doc_id": "doc02", "category": "factual", "difficulty": "easy",
         "query": "Who are the two parties that entered into the Mutual Non-Disclosure Agreement?",
         "ground_truth_answer": "The Agreement is between Apex Ventures LLC and Helix Dynamics Corp.",
         "key_snippets": ["Apex Ventures LLC", "Helix Dynamics Corp"]},
        {"id": "q06", "doc_id": "doc02", "category": "factual", "difficulty": "medium",
         "query": "What encryption standards are mandated for electronic documents under the NDA?",
         "ground_truth_answer": "AES-256 encryption at rest and TLS 1.3 in transit.",
         "key_snippets": ["AES-256", "TLS 1.3"]},
        {"id": "q07", "doc_id": "doc02", "category": "factual", "difficulty": "easy",
         "query": "How long is the confidentiality term in effect and which state laws govern it?",
         "ground_truth_answer": "The term is three (3) years and it is governed by the laws of the State of Delaware.",
         "key_snippets": ["three (3) years", "State of Delaware"]},
        {"id": "q08", "doc_id": "doc02", "category": "analytical", "difficulty": "medium",
         "query": "Under what conditions is information excluded from confidentiality under this agreement?",
         "ground_truth_answer": "Information that becomes publicly known through no breach, is received from a third party without breach, or was independently developed.",
         "key_snippets": ["publicly known", "independently developed", "third party"]},

        # --- Doc 03 Resume ---
        {"id": "q09", "doc_id": "doc03", "category": "factual", "difficulty": "easy",
         "query": "What university did Dr. Sarah Chen receive her Ph.D. from?",
         "ground_truth_answer": "Stanford University in 2018.",
         "key_snippets": ["Stanford University", "2018"]},
        {"id": "q10", "doc_id": "doc03", "category": "factual", "difficulty": "medium",
         "query": "What is the patent number held by Dr. Sarah Chen and what is its title?",
         "ground_truth_answer": "US Patent #11,489,203 titled 'Adaptive Vector Quantization for High-Throughput Approximate Nearest Neighbor Lookups'.",
         "key_snippets": ["11,489,203", "Adaptive Vector Quantization"]},
        {"id": "q11", "doc_id": "doc03", "category": "analytical", "difficulty": "medium",
         "query": "What key engineering metrics did Dr. Sarah Chen achieve at HyperScale Labs?",
         "ground_truth_answer": "Indexed 800M vectors with 99.995% uptime, cut token latency by 42%, and reduced annual cloud costs by $1.8M.",
         "key_snippets": ["800M vectors", "42%", "$1.8M", "99.995%"]},
        {"id": "q12", "doc_id": "doc03", "category": "factual", "difficulty": "easy",
         "query": "How many TB of unstructured PDF data did Dr. Chen's pipeline process daily at Cognitive Dynamics?",
         "ground_truth_answer": "12TB of unstructured PDF datasets per day.",
         "key_snippets": ["12TB", "PDF datasets per day"]},

        # --- Doc 04 Incident Report ---
        {"id": "q13", "doc_id": "doc04", "category": "factual", "difficulty": "easy",
         "query": "What was the malicious dependency that caused security incident #SEC-2026-0419?",
         "ground_truth_answer": "The compromised dependency was 'pdf-formatter-core' v1.2.8.",
         "key_snippets": ["pdf-formatter-core", "v1.2.8"]},
        {"id": "q14", "doc_id": "doc04", "category": "analytical", "difficulty": "medium",
         "query": "What was the external command-and-control server and exfiltration mechanism identified?",
         "ground_truth_answer": "Base64 DNS tunneling to c2.shadow-network.org.",
         "key_snippets": ["c2.shadow-network.org", "DNS tunneling"]},
        {"id": "q15", "doc_id": "doc04", "category": "factual", "difficulty": "easy",
         "query": "Were customer documents compromised during incident SEC-2026-0419?",
         "ground_truth_answer": "Zero customer documents were accessed; egress firewalls blocked 99.4% of outbound requests.",
         "key_snippets": ["0 documents", "99.4%"]},
        {"id": "q16", "doc_id": "doc04", "category": "analytical", "difficulty": "hard",
         "query": "What preventative measures were deployed following the security incident?",
         "ground_truth_answer": "Hash-pinned SBOMs, eBPF-based runtime syscall enforcement, and multi-party code reviews.",
         "key_snippets": ["SBOM", "eBPF", "multi-party code reviews"]},

        # --- Doc 05 Roadmap Memo ---
        {"id": "q17", "doc_id": "doc05", "category": "factual", "difficulty": "easy",
         "query": "What is the strategic revenue target for DocuMind AI by Q4 2026?",
         "ground_truth_answer": "Reaching $4.5M ARR by Q4 2026 while maintaining 99.9% uptime SLA.",
         "key_snippets": ["$4.5M ARR", "99.9% uptime"]},
        {"id": "q18", "doc_id": "doc05", "category": "table", "difficulty": "medium",
         "query": "How much budget is allocated for GPU compute and who is the vendor in the H2 roadmap?",
         "ground_truth_answer": "$320,000 allocated to Lambda Labs / RunPod to support 50k concurrent requests.",
         "key_snippets": ["$320,000", "Lambda Labs", "50k concurrent requests"]},
        {"id": "q19", "doc_id": "doc05", "category": "factual", "difficulty": "medium",
         "query": "What retrieval feature is scheduled for release v2.0 in Q3?",
         "ground_truth_answer": "Deep Hybrid Retrieval combining BM25 lexical keyword matching with dense vector representations from Gemini-Embedding-2.",
         "key_snippets": ["Deep Hybrid Retrieval", "BM25", "Gemini-Embedding-2"]},
        {"id": "q20", "doc_id": "doc05", "category": "table", "difficulty": "easy",
         "query": "What is the budget allocation for Managed Vector Storage in H2?",
         "ground_truth_answer": "$140,000 allocated to Qdrant Cloud Enterprise.",
         "key_snippets": ["$140,000", "Qdrant Cloud Enterprise"]},

        # --- Doc 06 Software Spec ---
        {"id": "q21", "doc_id": "doc06", "category": "factual", "difficulty": "medium",
         "query": "What is the capacity of the Layer 1 local LRU cache in the distributed caching specification?",
         "ground_truth_answer": "5,000 item capacity using Python cachetools.",
         "key_snippets": ["5,000", "LRU cache", "cachetools"]},
        {"id": "q22", "doc_id": "doc06", "category": "analytical", "difficulty": "hard",
         "query": "What are the exact TTL rules for document embeddings versus semantic queries?",
         "ground_truth_answer": "Document embeddings have a TTL of strictly 14 days, while semantic queries expire after 4 hours.",
         "key_snippets": ["14 days", "4 hours"]},
        {"id": "q23", "doc_id": "doc06", "category": "factual", "difficulty": "medium",
         "query": "What circuit breaker failure threshold triggers the transition to the OPEN state?",
         "ground_truth_answer": "Failure rate exceeding 25% over a 60-second window with at least 40 requests.",
         "key_snippets": ["25%", "60-second window", "40 requests"]},
        {"id": "q24", "doc_id": "doc06", "category": "factual", "difficulty": "easy",
         "query": "How frequently are Redis RDB snapshots pushed to S3 and to which AWS region?",
         "ground_truth_answer": "Every 3 hours to encrypted S3 buckets in us-east-1.",
         "key_snippets": ["3 hours", "us-east-1"]},

        # --- Doc 07 Financial Report ---
        {"id": "q25", "doc_id": "doc07", "category": "table", "difficulty": "easy",
         "query": "What was the total full-year revenue for Nexus Technologies in 2025?",
         "ground_truth_answer": "$142.8M total revenue for full year 2025.",
         "key_snippets": ["$142.8M", "Full Year 2025"]},
        {"id": "q26", "doc_id": "doc07", "category": "table", "difficulty": "medium",
         "query": "How much revenue was generated from Cloud Subscriptions in Q3 2025?",
         "ground_truth_answer": "$30.8M from Cloud Subscriptions in Q3 2025.",
         "key_snippets": ["$30.8M", "Q3 2025"]},
        {"id": "q27", "doc_id": "doc07", "category": "analytical", "difficulty": "medium",
         "query": "What percentage of total operating expenses was dedicated to R&D in 2025?",
         "ground_truth_answer": "R&D represented $48.2M, or 49.0% of total operating expenses.",
         "key_snippets": ["$48.2M", "49.0%"]},
        {"id": "q28", "doc_id": "doc07", "category": "factual", "difficulty": "easy",
         "query": "How much cash and cash equivalents did Nexus Technologies hold at the end of 2025?",
         "ground_truth_answer": "$68.4M in cash and cash equivalents, plus $24.0M in US Treasury bills.",
         "key_snippets": ["$68.4M", "$24.0M"]},

        # --- Doc 08 HR Handbook ---
        {"id": "q29", "doc_id": "doc08", "category": "factual", "difficulty": "easy",
         "query": "What are the core collaboration hours required by Vortex Global?",
         "ground_truth_answer": "10:00 AM to 3:00 PM in each employee's local timezone.",
         "key_snippets": ["10:00 AM to 3:00 PM"]},
        {"id": "q30", "doc_id": "doc08", "category": "factual", "difficulty": "easy",
         "query": "What is the home-office setup stipend and monthly internet reimbursement?",
         "ground_truth_answer": "$1,500 initial setup stipend and $150 monthly reimbursement.",
         "key_snippets": ["$1,500", "$150 monthly"]},
        {"id": "q31", "doc_id": "doc08", "category": "factual", "difficulty": "medium",
         "query": "How many days of paid vacation and sick leave are employees entitled to annually?",
         "ground_truth_answer": "25 days of vacation leave and 10 days of paid sick leave.",
         "key_snippets": ["25 days", "10 days"]},
        {"id": "q32", "doc_id": "doc08", "category": "factual", "difficulty": "medium",
         "query": "What is the 401(k) company match offered by Vortex Global?",
         "ground_truth_answer": "100% match on the first 5% of salary, vesting immediately on day one.",
         "key_snippets": ["100%", "first 5%", "vesting immediately"]},

        # --- Doc 09 Clinical Trial ---
        {"id": "q33", "doc_id": "doc09", "category": "factual", "difficulty": "medium",
         "query": "What disease condition is being treated in the clinical trial for VX-709?",
         "ground_truth_answer": "Moderate-to-severe ulcerative colitis.",
         "key_snippets": ["ulcerative colitis", "moderate-to-severe"]},
        {"id": "q34", "doc_id": "doc09", "category": "factual", "difficulty": "medium",
         "query": "What are the age requirements for patient inclusion in protocol NCT05829104?",
         "ground_truth_answer": "Age 18 to 70 years at the time of signing consent.",
         "key_snippets": ["18 to 70 years"]},
        {"id": "q35", "doc_id": "doc09", "category": "analytical", "difficulty": "hard",
         "query": "What are the three treatment arms and dosage strengths in the study?",
         "ground_truth_answer": "Arm A (15mg once daily), Arm B (30mg once daily), Arm C (matched placebo once daily).",
         "key_snippets": ["15mg", "30mg", "Placebo"]},
        {"id": "q36", "doc_id": "doc09", "category": "factual", "difficulty": "medium",
         "query": "Within what timeframe must Serious Adverse Events be reported to the Medical Monitor?",
         "ground_truth_answer": "Within 24 hours of site awareness.",
         "key_snippets": ["24 hours", "Serious Adverse Events"]},

        # --- Doc 10 Cloud Migration ---
        {"id": "q37", "doc_id": "doc10", "category": "factual", "difficulty": "easy",
         "query": "How many microservices are targeted for migration to Amazon EKS within 180 days?",
         "ground_truth_answer": "42 core microservices.",
         "key_snippets": ["42 core microservices", "180 days"]},
        {"id": "q38", "doc_id": "doc10", "category": "factual", "difficulty": "medium",
         "query": "What database migration tool is used to move PostgreSQL to Aurora and what is the downtime window?",
         "ground_truth_answer": "AWS Database Migration Service (DMS) with continuous CDC; cutover downtime window under 15 minutes.",
         "key_snippets": ["AWS Database Migration Service", "15 minutes"]},
        {"id": "q39", "doc_id": "doc10", "category": "analytical", "difficulty": "medium",
         "query": "What are the RTO and RPO disaster recovery targets across AWS regions?",
         "ground_truth_answer": "RTO under 30 minutes and RPO under 5 minutes between us-east-1 and us-west-2.",
         "key_snippets": ["RTO", "30 minutes", "RPO", "5 minutes"]},

        # --- Doc 11 GDPR Policy ---
        {"id": "q40", "doc_id": "doc11", "category": "factual", "difficulty": "easy",
         "query": "What is the contact email and address for the Data Protection Officer?",
         "ground_truth_answer": "dpo@documind.eu at Rue de la Loi 200, 1040 Brussels, Belgium.",
         "key_snippets": ["dpo@documind.eu", "Brussels"]},
        {"id": "q41", "doc_id": "doc11", "category": "factual", "difficulty": "easy",
         "query": "Within how many calendar days must a Data Subject Access Request (DSAR) be fulfilled?",
         "ground_truth_answer": "Within thirty (30) calendar days.",
         "key_snippets": ["thirty (30) calendar days", "30"]},
        {"id": "q42", "doc_id": "doc11", "category": "factual", "difficulty": "medium",
         "query": "What is the maximum administrative fine under GDPR Article 83?",
         "ground_truth_answer": "Up to €20,000,000 or 4% of total worldwide annual turnover.",
         "key_snippets": ["€20,000,000", "4%"]},

        # --- Doc 12 API Developer Guide ---
        {"id": "q43", "doc_id": "doc12", "category": "factual", "difficulty": "easy",
         "query": "What is the production base URL for the DocuMind API?",
         "ground_truth_answer": "https://api.documind.ai/v1",
         "key_snippets": ["https://api.documind.ai/v1"]},
        {"id": "q44", "doc_id": "doc12", "category": "factual", "difficulty": "medium",
         "query": "What are the default rate limits for the Standard Tier API keys?",
         "ground_truth_answer": "120 requests per minute and 10,000 requests per day.",
         "key_snippets": ["120 requests per minute", "10,000 requests per day"]},

        # --- Doc 18 Pharmacokinetics & Doc 19 Semiconductor ---
        {"id": "q45", "doc_id": "doc18", "category": "analytical", "difficulty": "hard",
         "query": "What was the mean elimination half-life and primary clearance pathway for the kinase inhibitor?",
         "ground_truth_answer": "Half-life of 14.8 hours with predominant hepatic metabolism via CYP3A4.",
         "key_snippets": ["14.8 hours", "CYP3A4", "hepatic metabolism"]},

        # --- Out of Scope Queries (Should be rejected / ungrounded) ---
        {"id": "q46", "doc_id": None, "category": "out_of_scope", "difficulty": "easy",
         "query": "What was the final score of the 2026 FIFA World Cup championship match?",
         "ground_truth_answer": "The document does not contain this information.",
         "key_snippets": ["not contain", "unsupported", "cannot find"]},
        {"id": "q47", "doc_id": None, "category": "out_of_scope", "difficulty": "easy",
         "query": "What is the secret recipe for Kentucky Fried Chicken?",
         "ground_truth_answer": "The document does not contain this information.",
         "key_snippets": ["not contain", "unsupported", "cannot find"]},
        {"id": "q48", "doc_id": None, "category": "out_of_scope", "difficulty": "medium",
         "query": "What is the exact stock price of Apple Inc. on December 1, 2029?",
         "ground_truth_answer": "The document does not contain this information.",
         "key_snippets": ["not contain", "unsupported", "cannot find"]},
        {"id": "q49", "doc_id": None, "category": "out_of_scope", "difficulty": "medium",
         "query": "Who won the Academy Award for Best Actor in the year 1954?",
         "ground_truth_answer": "The document does not contain this information.",
         "key_snippets": ["not contain", "unsupported", "cannot find"]},
        {"id": "q50", "doc_id": None, "category": "out_of_scope", "difficulty": "easy",
         "query": "How do you manufacture enriched uranium centrifuges at home?",
         "ground_truth_answer": "The document does not contain this information.",
         "key_snippets": ["not contain", "unsupported", "cannot find"]}
    ]

    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump({"documents": docs_info, "queries": queries}, f, indent=2)

    print(f"Successfully generated {len(docs_info)} documents in {DATASET_DIR}")
    print(f"Successfully generated {len(queries)} ground truth queries in {GROUND_TRUTH_FILE}")

if __name__ == "__main__":
    generate_all_documents()
