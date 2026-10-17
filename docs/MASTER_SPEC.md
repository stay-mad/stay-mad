
# STAY MAD
## AI-Powered Event Intelligence & Situational Awareness

You are an expert **Product Engineer, AI Engineer, Data Engineer, UX Engineer, and Google Cloud Architect**.

Your task is to design and build a **fully working functional prototype** called **Stay Mad**.

This prototype is being developed for an AI innovation competition with the following judging priorities:

- **Technical Merit & Gen AI Implementation — 40%**
- **Problem Alignment & Impact — 25%**
- **Innovation & Creativity — 25%**
- **User Experience & Solution Design — 10%**

The implementation MUST use **Google AI models, specifically Gemini/Gemma where appropriate**, and MUST be deployed on **Google Cloud using Cloud Run or Firebase**.

The final result must be a real, functional prototype that a judge can open and interact with.

It must NOT be a pitch deck, static mockup, fake dashboard, or superficial LLM wrapper.

---

# 1. CORE PRODUCT IDEA

## Product Name

**Stay Mad**

Possible interpretation:

**M.A.D. = Monitor · Analyze · Do**

Tagline:

> **Stay Mad, Stay Updated.**

Supporting statement:

> **Know what happened. Understand why it matters. Decide what you can do.**

---

# 2. THE PROBLEM

Modern people are exposed to fragmented information.

When a significant real-world event occurs, information arrives through:

- news articles
- local media
- government announcements
- official reports
- multiple updates
- different timestamps
- different geographic references

A single real-world event may produce dozens of articles.

Users must manually:

- identify which articles refer to the same event
- compare sources
- determine what actually happened
- reconstruct the timeline
- identify what changed
- understand why it matters
- determine who is affected
- determine whether they need to do anything

This creates information overload and makes situational awareness difficult.

---

# 3. THE SOLUTION

Stay Mad is an **AI-powered Event Intelligence platform**.

The fundamental idea is:

> **Do not organize news around articles. Organize news around real-world events.**

Instead of showing:

```text
Article
Article
Article
Article
Article
```

Stay Mad should transform fragmented information into:

```text
                    REAL-WORLD EVENT
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
           Timeline      Impact       Location
              │            │            │
              └────────────┼────────────┘
                           ↓
                    What Changed?
                           ↓
                    What Can I Do?
```

---

# 4. CORE DIFFERENTIATION

Stay Mad must NOT be positioned as:

- a generic news aggregator
- a news summarizer
- a chatbot over news
- a trending-news dashboard
- a simple Google News clone

The key differentiation is:

## EVENT INTELLIGENCE

The system reconstructs the **event behind the articles**.

For example:

```text
20 articles
8 sources
143 extracted claims
        ↓
AI Event Resolution
        ↓
1 canonical event
        ↓
1 reconstructed timeline
        ↓
impact + confidence + actions
```

This transformation is the central innovation of the product.

---

# 5. CORE USER QUESTION

Every major event should answer:

### WHAT HAPPENED?

A concise factual explanation.

### WHAT CHANGED?

What has changed since the previous known state.

### WHY DOES IT MATTER?

Explain real-world impact.

### WHO IS AFFECTED?

Identify affected people, organizations, locations, or infrastructure.

### WHAT CAN I DO?

Provide practical actions only when justified by reliable sources.

### WHAT IS STILL UNKNOWN?

Explicitly expose uncertainty and conflicting information.

---

# 6. TARGET USERS

Initial target:

### Everyday information-conscious users

People who want to understand:

- what is happening near them
- what is happening in their country
- what major events are happening globally
- which events actually matter
- what has changed since they last checked

Secondary future users:

- journalists
- researchers
- emergency-response organizations
- NGOs
- businesses
- analysts
- public-sector organizations

Do NOT build specialized enterprise functionality in the MVP.

---

# 7. INITIAL MVP SCOPE

Start with:

## Geography

Primary:

**Indonesia**

Hierarchy:

```text
City
 ↓
Province
 ↓
Country
```

The data model MUST support future expansion:

```text
City
 ↓
Province / State
 ↓
Country
 ↓
Continent
 ↓
World
```

---

# 8. INITIAL CATEGORIES

Support:

1. Disaster & Weather
2. Public Safety
3. Government & Public Policy
4. Economy
5. Transportation & Infrastructure
6. Technology & Cybersecurity
7. Health
8. Environment
9. Conflict & Humanitarian
10. Science

Do not attempt to implement every possible news category.

---

# 9. IMPORTANT VS TRENDING

This is a core product principle.

Do NOT assume:

```text
Trending = Important
```

Instead distinguish:

```text
IMPORTANT
URGENT
LOCAL
DEVELOPING
TRENDING
INFORMATIONAL
```

A viral celebrity story may be trending but have low public importance.

A local flood warning may have little social engagement but high importance.

The system must prioritize **real-world relevance over popularity**.

Trending should be a separate lens rather than the primary ranking mechanism.

---

# 10. CORE AI ARCHITECTURE

Gemini must be a meaningful component of the system.

Do NOT use Gemini only for final text summarization.

Gemini should participate in the reasoning pipeline:

```text
RAW ARTICLES
     ↓
CLAIM EXTRACTION
     ↓
ENTITY EXTRACTION
     ↓
TEMPORAL EXTRACTION
     ↓
LOCATION EXTRACTION
     ↓
EVENT CANDIDATES
     ↓
EVENT RESOLUTION
     ↓
CONFLICT DETECTION
     ↓
TIMELINE RECONSTRUCTION
     ↓
IMPACT ANALYSIS
     ↓
ACTIONABILITY
     ↓
FINAL EVENT INTELLIGENCE
```

This is the central Gen AI implementation.

---

# 11. GOOGLE GEMINI REQUIREMENT

Use a current appropriate Google Gemini model through Google's supported SDK/API.

Use structured outputs wherever possible.

Gemini should be used for:

### A. Claim extraction

Extract factual claims from articles.

### B. Entity extraction

Identify:

- people
- organizations
- locations
- infrastructure
- events
- institutions

### C. Temporal reasoning

Identify:

- when something happened
- when something was reported
- when something was announced
- when something changed

### D. Event resolution

Determine whether articles describe:

- the same event
- related events
- separate events

### E. Conflict detection

Identify contradictions or uncertainty.

### F. Timeline synthesis

Reconstruct chronological event progression.

### G. Impact analysis

Explain real-world relevance based on available evidence.

### H. Actionability

Identify whether practical action exists and summarize it only from trustworthy information.

---

# 12. GEMINI MUST NOT HALLUCINATE

All AI-generated factual statements must be grounded in available sources.

The system must distinguish:

```text
CONFIRMED
SUPPORTED
UNCONFIRMED
CONFLICTING
UNKNOWN
```

If information is unavailable:

> "Not enough information available."

Do not invent:

- numbers
- timestamps
- locations
- casualties
- government statements
- recommended actions
- causes
- motivations

---

# 13. CLAIM-CENTERED ARCHITECTURE

Do not send a large collection of articles directly to Gemini and ask:

> "Summarize these articles."

Instead use structured intermediate data.

Example:

```json
{
  "claim": "Flooding affected several districts",
  "subject": "Flooding",
  "predicate": "affected",
  "object": "several districts",
  "location": "Jakarta",
  "event_time": "...",
  "source_id": "...",
  "confidence": 0.91
}
```

Claims become evidence for Events.

---

# 14. EVENT RESOLUTION ENGINE

The most important backend component is:

## Event Resolution Engine

Conceptual pipeline:

```text
Articles
   ↓
Claims
   ↓
Entities
   ↓
Time
   ↓
Location
   ↓
Semantic Similarity
   ↓
Temporal Similarity
   ↓
Geographic Similarity
   ↓
Entity Overlap
   ↓
Gemini Reasoning
   ↓
Canonical Event
```

Use a hybrid strategy:

- deterministic rules
- embeddings
- metadata
- temporal constraints
- geographic constraints
- Gemini reasoning

Do NOT rely exclusively on LLM calls.

Do NOT rely exclusively on vector similarity.

---

# 15. EXAMPLE EVENT CLUSTERING

Input:

```text
Article A:
Flooding reported in East Jakarta.

Article B:
Several roads in East Jakarta are submerged.

Article C:
BPBD reports flooding in East Jakarta.

Article D:
Residents evacuated from affected areas.
```

Expected:

```text
EVENT

Flooding in East Jakarta
```

Not four independent news items.

---

# 16. TEMPORAL INTELLIGENCE

The system MUST distinguish:

```text
event_time
reported_time
published_time
updated_time
```

Example:

Article:

```text
Published: 14:00

"The flooding began around 08:30."
```

Timeline:

```text
08:30 — Flooding begins
```

NOT:

```text
14:00 — Flooding begins
```

If exact timing is uncertain, preserve uncertainty.

Example:

```text
Around 08:30
```

rather than inventing:

```text
08:30:00
```

---

# 17. EVENT TIMELINE

Each event should have a timeline.

Example:

```text
07:20
Heavy rainfall begins

08:10
First flooding reported

09:35
Multiple roads affected

10:15
Official warning issued

12:30
Evacuation begins

14:20
Water levels begin decreasing
```

Each timeline entry should reference its evidence/source.

---

# 18. WHAT CHANGED

Implement a signature feature:

## WHAT CHANGED?

When an event receives new information, compare the current event state against the previous state.

Example:

```text
WHAT CHANGED SINCE 10:00?

+ 3 additional districts affected
+ Evacuation announced
+ 7 additional roads closed
- Rainfall intensity decreasing
```

This is a key differentiator.

Users often do not need to reread everything.

They want to know:

> **What changed since I last checked?**

---

# 19. EVENT CONFIDENCE

Every event should have:

```text
HIGH
MEDIUM
LOW
```

Confidence should consider:

- source quality
- independent corroboration
- claim consistency
- official confirmation
- temporal consistency
- geographic consistency

Example:

```text
HIGH CONFIDENCE

✓ Official source
✓ 5 independent reports
✓ Consistent location
✓ Consistent timeline
```

Confidence must be explainable.

---

# 20. CONFLICT DETECTION

If sources disagree, expose it.

Example:

```text
CONFLICTING INFORMATION

Source A:
7 districts affected

Source B:
5 districts affected

Official count has not yet been confirmed.
```

Do not silently choose one value.

This feature is important for trust and technical credibility.

---

# 21. IMPORTANCE ENGINE

Create an explainable importance score.

Initial configuration:

```text
Impact             30%
Urgency            20%
Proximity          15%
Public Importance  15%
Momentum           10%
Confidence         10%
```

These weights must be configurable.

The system should explain why an event is prioritized.

Example:

```text
WHY YOU ARE SEEING THIS

⚠ High public impact
📍 Relevant to Jakarta
⏱ Developing rapidly
✓ Multiple independent sources
```

Do not optimize exclusively for clicks.

---

# 22. ACTIONABILITY ENGINE

Classify events:

```text
ACTION REQUIRED
ACTION RECOMMENDED
OPTIONAL
INFORMATIONAL
NO IMMEDIATE ACTION
```

Actions must be grounded in reliable sources.

Example:

```text
FLOOD WARNING

WHAT YOU CAN DO

• Avoid affected roads
• Monitor official emergency updates
• Check on vulnerable family members
```

If there is no meaningful action:

```text
NO IMMEDIATE ACTION REQUIRED
```

Do not manufacture generic advice.

---

# 23. GEOGRAPHIC INTELLIGENCE

Every event should have geographic metadata.

Example:

```json
{
  "city": "Jakarta",
  "province": "DKI Jakarta",
  "country": "Indonesia",
  "continent": "Asia"
}
```

The UI must support:

```text
World
 ↓
Asia
 ↓
Indonesia
 ↓
Jakarta
```

Future architecture must support arbitrary geographic levels.

---

# 24. EVENT GRAPH

Create a conceptual event graph.

Example:

```text
Heavy Rain
    │
    ↓
Flooding
    │
 ┌──┴──────────────┐
 ↓                 ↓
Road Closure    Evacuation
 ↓                 ↓
Transport       Residents
Disruption
```

Events should be able to have relationships:

```text
caused_by
affected
related_to
followed_by
escalated_to
resolved_by
```

For MVP, implement only the relationships that are necessary.

Do not over-engineer a full knowledge graph if it is unnecessary.

---

# 25. CORE USER EXPERIENCE

The product should have three primary screens.

---

## SCREEN 1 — DAILY OVERVIEW

Example:

```text
STAY MAD

Jakarta · Today

────────────────────────

🔴 NEED TO KNOW

Flooding in East Jakarta
High impact · Developing

Major commuter disruption
Medium impact

────────────────────────

📍 AROUND YOU

6 meaningful events

────────────────────────

WHAT CHANGED

4 events changed significantly today

────────────────────────

🇮🇩 INDONESIA

12 major developments

────────────────────────

🌏 WORLD

8 major developments
```

The page must be scannable within seconds.

---

# 26. SCREEN 2 — EVENT DETAIL

Example:

```text
FLOODING IN EAST JAKARTA

DEVELOPING
HIGH CONFIDENCE

────────────────────────

WHAT HAPPENED

Heavy rainfall caused flooding across
multiple areas of East Jakarta.

────────────────────────

TIMELINE

07:20
Heavy rainfall begins

08:10
Flooding reported

09:35
Roads affected

10:15
Official warning issued

────────────────────────

WHAT CHANGED

+ 3 districts affected
+ Evacuation announced

────────────────────────

WHY IT MATTERS

Transportation and public safety
may be affected.

────────────────────────

WHO IS AFFECTED

Residents and commuters in
affected districts.

────────────────────────

WHAT YOU CAN DO

• Avoid affected roads
• Monitor official alerts

────────────────────────

WHAT IS UNCLEAR

Exact number of displaced residents
has not yet been confirmed.

────────────────────────

SOURCES

Source A
Source B
Source C
...
```

---

# 27. SCREEN 3 — AI REASONING / TRANSPARENCY

Create a lightweight transparency view.

Example:

```text
HOW STAY MAD UNDERSTOOD THIS EVENT

26 articles analyzed

↓

143 claims extracted

↓

4 candidate events identified

↓

18 claims associated with this event

↓

3 conflicting claims detected

↓

11 temporal references resolved

↓

Timeline generated

↓

Confidence: HIGH
```

This is critical for demonstrating meaningful Gen AI implementation to judges.

---

# 28. HOME FEED DESIGN PRINCIPLE

The product should NOT feel like an infinite-scroll social feed.

Avoid:

- clickbait
- sensational headlines
- excessive notifications
- engagement manipulation
- dark patterns

The design should feel:

- calm
- trustworthy
- intelligent
- modern
- focused
- information-dense but readable

---

# 29. NEWS INGESTION

Prefer:

1. RSS
2. Official APIs
3. Government sources
4. Trusted publishers

Use scraping only where legally and technically appropriate.

Respect:

- robots.txt
- Terms of Service
- copyright
- rate limits

Do not reproduce entire articles.

Store only necessary metadata and extracted information.

Always provide source attribution and original links.

---

# 30. DEMO DATA STRATEGY

The prototype must support both:

```text
LIVE DATA
+
SEEDED DEMO DATA
```

This is critical for reliable judging.

Do not depend entirely on live news during a presentation.

Create a deterministic seeded dataset containing several events.

Example:

```text
Event A
Flooding in Jakarta
8 articles

Event B
Volcanic activity
5 articles

Event C
Transportation disruption
4 articles

Event D
Economic policy update
6 articles
```

The seeded dataset must demonstrate:

- duplicate articles
- multiple sources
- conflicting claims
- different publication times
- actual event times
- geographic metadata
- evolving event updates

Clearly label demo data if necessary.

---

# 31. EVALUATION DATASET

Create a small evaluation dataset.

Target:

```text
50–100 articles
10–20 known events
```

Create ground truth for:

- article → event mapping
- location
- event category
- timeline ordering
- claim correctness

Measure:

```text
Event clustering accuracy
Timeline accuracy
Location accuracy
Claim extraction accuracy
Source attribution accuracy
```

Do NOT fabricate metrics.

Only show metrics after actual evaluation.

---

# 32. TECHNICAL ARCHITECTURE

Preferred architecture:

```text
                 NEWS SOURCES
                      │
                      ↓
             ┌─────────────────┐
             │ Ingestion Layer │
             └────────┬────────┘
                      ↓
             ┌─────────────────┐
             │ Article Store   │
             └────────┬────────┘
                      ↓
             ┌─────────────────┐
             │ Gemini          │
             │ Claim Extraction│
             └────────┬────────┘
                      ↓
             ┌─────────────────┐
             │ Event Resolution│
             │ Engine          │
             └────────┬────────┘
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
    Timeline      Geography      Claims
        │             │             │
        └─────────────┼─────────────┘
                      ↓
             ┌─────────────────┐
             │ Event           │
             │ Intelligence    │
             └────────┬────────┘
                      ↓
             ┌─────────────────┐
             │ REST API        │
             └────────┬────────┘
                      ↓
             ┌─────────────────┐
             │ Web Application │
             └─────────────────┘
                      ↓
                  CLOUD RUN
```

---

# 33. GOOGLE CLOUD

The solution MUST be deployable on Google Cloud.

Preferred:

```text
Frontend
    ↓
Cloud Run

Backend
    ↓
Cloud Run

Database
    ↓
Cloud SQL PostgreSQL
```

Use:

- Cloud Run
- Cloud SQL
- Secret Manager
- Artifact Registry
- Cloud Logging

Use Firebase if it materially improves the prototype experience.

Do not add unnecessary Google Cloud services simply for appearance.

---

# 34. PREFERRED TECH STACK

Frontend:

- Next.js
- React
- TypeScript
- Tailwind CSS

Backend:

- Python
- FastAPI

AI:

- Google Gemini
- Google GenAI SDK

Database:

- PostgreSQL

Optional:

- pgvector
- Redis

Deployment:

- Docker
- Cloud Run
- GitHub Actions if appropriate

---

# 35. ARCHITECTURAL PRINCIPLE

Do NOT over-engineer the prototype.

Prefer:

```text
Modular Monolith
```

over:

```text
Multiple microservices
```

unless there is a clear reason.

The architecture should nevertheless separate logical modules:

```text
ingestion
extraction
event_resolution
timeline
ranking
actionability
api
```

This provides a clean path toward future scale.

---

# 36. SCALABILITY

The prototype should demonstrate a credible path from:

```text
Indonesia
10–20 sources
hundreds of articles/day
```

to:

```text
Asia
hundreds of sources
millions of articles
```

without requiring a complete rewrite.

Use source adapters:

```text
RSS Adapter
API Adapter
Government Adapter
Publisher Adapter
```

Normalize all inputs into a common article schema.

---

# 37. COST CONTROL

Gemini calls must be minimized.

Use deterministic processing for:

- HTML parsing
- hashing
- duplicate detection
- metadata extraction
- simple date parsing

Use embeddings for candidate retrieval where appropriate.

Use Gemini for higher-level reasoning.

Cache Gemini results.

Do not repeatedly process unchanged articles.

---

# 38. DATABASE ENTITIES

At minimum support:

```text
Source
Article
Claim
Event
EventClaim
TimelineEntry
Location
Action
EventRelation
ProcessingJob
```

Use proper foreign keys and indexes.

---

# 39. API REQUIREMENTS

Create APIs for:

```text
GET /events
GET /events/{id}
GET /events/{id}/timeline
GET /events/{id}/sources
GET /events/{id}/changes
GET /events/{id}/analysis
GET /locations
```

Internal processing APIs may be added as needed.

Provide OpenAPI documentation.

---

# 40. OBSERVABILITY

Log meaningful pipeline stages:

```text
article_ingested
article_normalized
claim_extracted
event_candidate_created
event_merged
event_split
timeline_generated
conflict_detected
confidence_calculated
event_published
```

Include correlation IDs.

Make AI processing debuggable.

---

# 41. SECURITY

Implement:

- HTTPS
- secure secret management
- input validation
- URL validation
- SSRF protection for fetching remote URLs
- HTML sanitization
- rate limiting where appropriate
- no exposed API keys
- no arbitrary code execution

Never hardcode credentials.

Use Google Cloud Secret Manager or secure environment configuration.

---

# 42. LEGAL / CONTENT REQUIREMENTS

Do not reproduce complete copyrighted articles.

Use:

- title
- metadata
- extracted facts
- concise generated summaries
- source attribution
- original URL

Users should be able to access the original source.

---

# 43. JUDGING CRITERIA MAPPING

The implementation must explicitly satisfy the following.

---

## 43.1 TECHNICAL MERIT & GEN AI — 40%

### Meaningful Gen AI

Demonstrate that Gemini directly performs:

- claim extraction
- event resolution
- temporal reasoning
- conflict detection
- timeline synthesis
- impact analysis
- actionability

### Technical implementation

Demonstrate:

- real ingestion
- real processing
- real database
- real Gemini API integration
- structured outputs
- validation
- error handling
- deployed application

### Scalability

Demonstrate:

- modular architecture
- source adapters
- normalized schema
- event-centric architecture
- Cloud Run deployment
- scalable processing design

---

# 44. PROBLEM ALIGNMENT & IMPACT — 25%

The prototype must clearly demonstrate:

```text
Fragmented information
        ↓
Information overload
        ↓
AI event reconstruction
        ↓
Situational awareness
```

Impact should be demonstrated through concrete examples:

- disaster awareness
- transportation disruption
- public policy changes
- public safety
- environmental events

Do not claim unsupported social impact numbers.

---

# 45. INNOVATION & CREATIVITY — 25%

The core innovation is:

## EVENT-FIRST NEWS INTELLIGENCE

Not:

```text
Article → Summary
```

But:

```text
Articles
    ↓
Claims
    ↓
Events
    ↓
Timeline
    ↓
Change detection
    ↓
Impact
    ↓
Action
```

Signature features:

1. Event Resolution
2. Timeline Reconstruction
3. What Changed
4. Geographic Zoom
5. Confidence + Conflict Awareness
6. Actionability

Do not describe basic LLM summarization as the primary innovation.

---

# 46. USER EXPERIENCE & SOLUTION DESIGN — 10%

Prioritize:

- fast comprehension
- clear hierarchy
- accessible typography
- responsive layout
- minimal cognitive load
- source transparency
- clear AI-generated labeling
- understandable uncertainty

A user should understand the core event within seconds.

---

# 47. DEMO STRATEGY

The demo should be designed around the judging criteria.

Recommended flow:

### STEP 1 — Problem

Show:

```text
26 articles
8 sources
1 event
```

Explain that information is fragmented.

### STEP 2 — AI Processing

Show:

```text
26 articles
↓
143 claims
↓
4 candidate events
↓
1 canonical event
```

### STEP 3 — Event

Open the consolidated event.

### STEP 4 — Timeline

Show chronological reconstruction.

### STEP 5 — What Changed

Show the newest development.

### STEP 6 — Impact

Show:

```text
Why it matters
Who is affected
```

### STEP 7 — Action

Show practical actions when justified.

### STEP 8 — Trust

Show:

```text
Sources
Confidence
Conflicts
```

### STEP 9 — AI Transparency

Show:

```text
How Stay Mad understood this event
```

### STEP 10 — Architecture

Show:

```text
Gemini
+
Event Resolution Engine
+
Cloud Run
```

---

# 48. EXPECTED "WOW MOMENT"

The primary wow moment should be:

```text
26 fragmented articles
        ↓
      Gemini
        ↓
ONE EVENT
        ↓
COHERENT TIMELINE
        ↓
WHAT CHANGED
        ↓
WHY IT MATTERS
        ↓
WHAT YOU CAN DO
```

This transformation must be visible and understandable to the judge.

---

# 49. WHAT NOT TO BUILD

Do NOT prioritize:

- social media
- comments
- user profiles
- complex authentication
- subscriptions
- advertising
- native mobile apps
- generic AI chatbot
- massive crawler infrastructure
- advanced recommendation engine
- sentiment dashboard
- unnecessary maps
- unnecessary notifications

These features do not directly improve the judging criteria enough to justify their complexity.

---

# 50. DEVELOPMENT PHASES

## PHASE 0 — Architecture

Before coding, produce:

1. PRD
2. User stories
3. Architecture
4. Data model
5. API specification
6. Gemini schemas
7. Gemini prompts
8. Event resolution strategy
9. Timeline strategy
10. Ranking strategy
11. UI specification
12. Google Cloud deployment architecture
13. Evaluation strategy
14. Risk register

---

## PHASE 1 — Foundation

Implement:

- repository
- frontend
- backend
- database
- configuration
- Docker
- Google Cloud setup

---

## PHASE 2 — Ingestion

Implement:

```text
Source
 ↓
Article
 ↓
Normalization
 ↓
Deduplication
```

---

## PHASE 3 — Gemini Extraction

Implement:

```text
Article
 ↓
Claims
Entities
Location
Time
Category
```

Use structured output.

---

## PHASE 4 — Event Resolution

Implement:

```text
Articles
 ↓
Candidate events
 ↓
Similarity
 ↓
Gemini reasoning
 ↓
Canonical events
```

---

## PHASE 5 — Timeline

Implement:

```text
Claims
 ↓
Temporal normalization
 ↓
Chronological timeline
```

---

## PHASE 6 — Intelligence

Implement:

- confidence
- conflict detection
- importance
- impact
- what changed
- actionability

---

## PHASE 7 — UX

Implement:

- Daily Overview
- Event Detail
- AI Transparency
- geographic filtering

---

## PHASE 8 — Evaluation

Run the evaluation dataset.

Measure actual performance.

Fix major errors.

---

## PHASE 9 — Google Cloud Deployment

Deploy:

- frontend
- backend
- database
- Gemini integration

Ensure the application is publicly accessible.

---

## PHASE 10 — Competition Demo

Prepare:

- demo dataset
- demo flow
- architecture diagram
- evaluation results
- limitations
- README
- deployment instructions

---

# 51. ACCEPTANCE CRITERIA

The prototype is complete only if all of these work:

### Data

- [ ] News sources can be ingested
- [ ] Articles are normalized
- [ ] Duplicate articles can be detected

### AI

- [ ] Gemini is actually integrated
- [ ] Claims are extracted
- [ ] Events are resolved
- [ ] Timeline is generated
- [ ] Conflicts can be detected
- [ ] Impact can be generated
- [ ] Actionability can be determined

### Product

- [ ] Daily overview works
- [ ] Event detail works
- [ ] Timeline works
- [ ] What Changed works
- [ ] Geographic filtering works
- [ ] Sources are visible
- [ ] Confidence is visible
- [ ] AI reasoning can be inspected

### Infrastructure

- [ ] Application runs locally
- [ ] Application is containerized
- [ ] Gemini credentials are secure
- [ ] Application is deployed to Google Cloud
- [ ] Cloud Run deployment works
- [ ] Public URL works

### Competition

- [ ] Core innovation is immediately understandable
- [ ] AI contribution is demonstrable
- [ ] Demo is reproducible
- [ ] No fabricated metrics
- [ ] Known limitations are documented

---

# 52. IMPORTANT DEVELOPMENT RULE

Do not start by building a beautiful UI.

Do not start by building a massive crawler.

Do not start by building authentication.

First prove:

```text
ARTICLES
   ↓
CLAIMS
   ↓
EVENT
   ↓
TIMELINE
```

This is the technical heart of Stay Mad.

Once this works reliably, build the experience around it.

---

# 53. REQUIRED OUTPUT BEFORE IMPLEMENTATION

Before writing application code, produce:

## A. Product Architecture

Explain all components and responsibilities.

## B. Data Model

Provide entity relationships and schemas.

## C. Gemini Architecture

For every Gemini call specify:

- purpose
- input
- output schema
- model usage
- validation
- fallback
- caching strategy

## D. Event Resolution Algorithm

Explain how articles become events.

## E. Timeline Algorithm

Explain how timestamps are extracted and normalized.

## F. Confidence Algorithm

Explain how confidence is calculated.

## G. Importance Algorithm

Explain how events are ranked.

## H. Actionability Algorithm

Explain when actions should or should not be shown.

## I. Evaluation Framework

Explain how quality will be measured.

## J. Google Cloud Architecture

Explain deployment and scaling.

## K. Risk Register

Identify:

- hallucination
- incorrect clustering
- temporal errors
- source reliability
- data sparsity
- cost
- latency
- scraping/legal risks
- deployment risks

---

# 54. FINAL PRODUCT DEFINITION

Stay Mad should ultimately demonstrate this transformation:

```text
                    THE OLD WAY

Article
Article
Article
Article
Article
Article
Article

        ↓

User manually connects everything


                    STAY MAD

Article ─┐
Article ─┤
Article ─┤
Article ─┤
Article ─┘
     ↓
   GEMINI
     ↓
  CLAIMS
     ↓
EVENT RESOLUTION
     ↓
CANONICAL EVENT
     ↓
┌───────────────────────────────┐
│ WHAT HAPPENED                 │
│                               │
│ TIMELINE                      │
│                               │
│ WHAT CHANGED                  │
│                               │
│ WHY IT MATTERS                │
│                               │
│ WHO IS AFFECTED               │
│                               │
│ WHAT YOU CAN DO               │
│                               │
│ WHAT IS UNKNOWN               │
│                               │
│ SOURCES + CONFIDENCE          │
└───────────────────────────────┘
```

The final product should make the following statement credible:

> **Stay Mad doesn't just summarize the news. It reconstructs the events behind the news.**

And the ultimate user experience should answer:

> **What happened? What changed? Why does it matter? What can I do?**

Build the prototype around proving this concept clearly, reliably, and technically.