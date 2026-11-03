-- Course Navigator -- SQLite schema (v1 prototype)
--
-- Every table traces to a decision in the elicitation running log
-- (MIS 430/final-project/elicitation/findings - running log.md, section 6).
-- Where this schema departs from "Course Navigator ERD (v1).pdf", the decision
-- ID is named inline. The running log overrides the ERD.
--
-- Cut from the ERD per D-22 (no hard-coded taxonomy):
--   topic, course_topic, career, career_topic, search_request.career_id
--   -> replaced by course.description, ranked by free-text phrase.
-- Deferred per D-23: NEW seminar themes (CC / ESC / SPSC). Banner has no attribute.
-- Deferred as optional-for-v1: prerequisite, instructor as entities.

PRAGMA foreign_keys = ON;


-- ---------------------------------------------------------------------------
-- People and access
-- ---------------------------------------------------------------------------

CREATE TABLE advisor (
    advisor_id  INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT
);

-- D-25: one advisor per student, so this is a plain FK, not a join table.
CREATE TABLE student (
    student_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT,
    classification TEXT,            -- Freshman | Sophomore | Junior | Senior
    catalog_year TEXT,
    advisor_id   INTEGER REFERENCES advisor(advisor_id),
    -- D-22: the depth study is NOT a controlled record. This is a free-text
    -- working label only. Ranking never reads it; it reads the typed phrase.
    depth_study_label TEXT
);

-- D-25: roles are student and advisor only. The student records person (F-39)
-- gets no role. D-20/F-40: both students and advisors need a login.
-- No auth provider in v1 (handoff constraint) -- this is identity, not security.
CREATE TABLE app_user (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT    NOT NULL UNIQUE,
    display_name TEXT   NOT NULL,
    role        TEXT    NOT NULL CHECK (role IN ('student', 'advisor')),
    student_id  INTEGER REFERENCES student(student_id),
    advisor_id  INTEGER REFERENCES advisor(advisor_id),
    -- a login points at exactly one person record, matching its role
    CHECK ((role = 'student' AND student_id IS NOT NULL AND advisor_id IS NULL)
        OR (role = 'advisor' AND advisor_id IS NOT NULL AND student_id IS NULL))
);


-- ---------------------------------------------------------------------------
-- Requirements
-- ---------------------------------------------------------------------------

-- A gen-ed bucket is one Banner section attribute that counts toward a
-- requirement. Only the 12 allowlisted attributes become buckets; the other 14
-- Banner attributes (PW:*, University Honors, Dining Dollars Exempt, ...) are
-- stored on offering_attribute with bucket_id NULL and never rank.
CREATE TABLE gen_ed_bucket (
    bucket_id    INTEGER PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,   -- short key used in the UI
    banner_attribute TEXT NOT NULL UNIQUE, -- exact Banner description, unescaped
    name         TEXT NOT NULL
);

-- A requirement is what a student must satisfy. Source: Pre-Advising Checklist
-- rev. Nov 2025, p.2. Note this is wider than running log section 4, which omits
-- Legends/Compass, first-year Composition and MATH 110 (logged as Q-25).
--
-- rule_kind:
--   bucket  -- satisfied by hours in a pool of buckets. Drives D-19 ranking.
--   numeric -- satisfied by an hours total. Displayed, never ranked on.
CREATE TABLE requirement (
    requirement_id INTEGER PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    system       TEXT NOT NULL CHECK (system IN ('core', 'university', 'new_college')),
    rule_kind    TEXT NOT NULL CHECK (rule_kind IN ('bucket', 'numeric')),
    hours_needed INTEGER,              -- NULL where the checklist states no hours
    min_courses  INTEGER,
    -- 8 hrs Natural Science "with at least two hours of lab". No Banner attribute
    -- carries lab; it is detected from course_offering.schedule_type.
    lab_hours_needed INTEGER NOT NULL DEFAULT 0,
    min_course_level INTEGER,          -- e.g. 300 for "36 hours at or above 300"
    note         TEXT
);

-- D-28: requirements are a UNION of buckets, not a hierarchy.
-- Verified against spring2027.csv: Literature co-tags Humanities 95% of the time
-- and World Language 93%, but Fine Arts only 10% and History/Social 0%. Modelling
-- nesting would silently drop courses; a union is immune to Banner's inconsistency.
--
-- is_must_include carries the checklist's "(including at least one course in
-- Literature)" and "(including at least one History)" clauses.
CREATE TABLE requirement_bucket (
    requirement_id  INTEGER NOT NULL REFERENCES requirement(requirement_id),
    bucket_id       INTEGER NOT NULL REFERENCES gen_ed_bucket(bucket_id),
    is_must_include INTEGER NOT NULL DEFAULT 0,
    min_hours       INTEGER,           -- hours required from this bucket specifically
    PRIMARY KEY (requirement_id, bucket_id)
);


-- ---------------------------------------------------------------------------
-- Catalog
-- ---------------------------------------------------------------------------

-- One row per subject+number. Descriptions are COURSE level, not section level:
-- verified live against POST /searchResults/getCourseDescription, where all
-- AAST 395 sections return the same generic blurb. 3,324 unique courses in
-- spring2027, so the cache is fetched once per course, not once per section.
CREATE TABLE course (
    course_id     INTEGER PRIMARY KEY,
    subject       TEXT NOT NULL,
    course_number TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    description_fetched_at TEXT,
    -- D-27: set when the description is the shared generic catalog blurb for a
    -- rotating-topic course. Drives the "ask your advisor" flag on PHRASE
    -- RELEVANCE only -- never on bucket closure. See recommendation.flag.
    topic_uncertain INTEGER NOT NULL DEFAULT 0,
    UNIQUE (subject, course_number)
);

-- One row per real offered section. D-16: grounding in the actually-offered list
-- is the differentiator, because AI tools recommend courses that are not offered
-- (F-26). Loaded from ua_classes.py output for one term.
CREATE TABLE course_offering (
    offering_id  INTEGER PRIMARY KEY,
    course_id    INTEGER NOT NULL REFERENCES course(course_id),
    term         TEXT NOT NULL,         -- Banner term code, e.g. 202710
    crn          TEXT NOT NULL,
    section      TEXT,
    credits      REAL,
    -- the to-be process filters on schedule, so these are first-class columns
    days         TEXT,                  -- MTWRF
    begin_time   TEXT,
    end_time     TEXT,
    building     TEXT,
    room         TEXT,
    schedule_type TEXT,                 -- 'Laboratory' satisfies the 2-hr lab rule
    instructional_method TEXT,
    campus       TEXT,
    part_of_term TEXT,
    instructors  TEXT,                  -- denormalised; instructor entity is v2
    max_enrollment  INTEGER,
    enrollment      INTEGER,
    seats_available INTEGER,
    open_section    INTEGER,
    section_text    TEXT,
    -- true when the section carries the Banner 'Special Topics Course' attribute
    -- (926 sections). NOT the same as topic_uncertain: 136 Legends sections carry
    -- it and are a known First-Year Compass requirement. See D-27.
    is_special_topics INTEGER NOT NULL DEFAULT 0,
    UNIQUE (term, crn)
);

-- Every Banner attribute on a section is kept. bucket_id is set only for the 12
-- allowlisted ones, so the other 14 stay auditable without ever ranking.
CREATE TABLE offering_attribute (
    offering_id  INTEGER NOT NULL REFERENCES course_offering(offering_id),
    attribute    TEXT NOT NULL,         -- exact Banner description, HTML-unescaped
    bucket_id    INTEGER REFERENCES gen_ed_bucket(bucket_id),
    PRIMARY KEY (offering_id, attribute)
);


-- ---------------------------------------------------------------------------
-- Student record
-- ---------------------------------------------------------------------------

-- D-24: completed coursework comes from DegreeWorks. Import mechanism is still
-- open; seeded demo data for the prototype. The shape holds either way.
CREATE TABLE completed_course (
    completed_id INTEGER PRIMARY KEY,
    student_id   INTEGER NOT NULL REFERENCES student(student_id),
    subject      TEXT NOT NULL,
    course_number TEXT NOT NULL,
    title        TEXT,
    term         TEXT,
    grade        TEXT,
    credits      REAL NOT NULL DEFAULT 0
);

-- Which buckets a completed course actually counted for.
-- Stored rather than re-derived: a course taken in 2024 carried that term's
-- attributes, and we only hold spring 2027's. DegreeWorks is the authority on
-- what counted (F-19), so we record its answer instead of guessing.
CREATE TABLE completed_course_bucket (
    completed_id INTEGER NOT NULL REFERENCES completed_course(completed_id),
    bucket_id    INTEGER NOT NULL REFERENCES gen_ed_bucket(bucket_id),
    PRIMARY KEY (completed_id, bucket_id)
);


-- ---------------------------------------------------------------------------
-- Search and results
-- ---------------------------------------------------------------------------

-- D-22: the phrase is the whole input. No stored topic, no career.
-- actor_user_id records WHO searched, because an advisor can search for an
-- advisee (D-01, D-25) -- that is a different act from the student searching.
CREATE TABLE search_request (
    request_id    INTEGER PRIMARY KEY,
    student_id    INTEGER NOT NULL REFERENCES student(student_id),
    actor_user_id INTEGER NOT NULL REFERENCES app_user(user_id),
    term          TEXT NOT NULL,
    phrase        TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- D-19: the ranked output. Score has two independent halves --
--   bucket_score    : hours this section closes against the student's OUTSTANDING
--                     requirements. Always trustworthy; comes from attributes.
--   relevance_score : TF-IDF similarity of the phrase to title + description.
--                     Unreliable when course.topic_uncertain is set.
--
-- Handoff asked us to pick one: the ERD says every recommendation points at a
-- real section, the process diagram also flagged "relevant but not offered".
-- RESOLVED -- offering_id is NOT NULL. Not-offered is dropped from v1, which is
-- the position D-16 requires anyway.
--
-- flag (D-21 as refined by D-27):
--   ranked          -- both halves trustworthy
--   topic_uncertain -- buckets are known, the TOPIC is not. Shown, never hidden,
--                      with "cannot determine -- ask your advisor" on relevance.
CREATE TABLE recommendation (
    recommendation_id INTEGER PRIMARY KEY,
    request_id    INTEGER NOT NULL REFERENCES search_request(request_id),
    offering_id   INTEGER NOT NULL REFERENCES course_offering(offering_id),
    rank          INTEGER NOT NULL,
    score         REAL NOT NULL,
    bucket_score  REAL NOT NULL DEFAULT 0,
    relevance_score REAL NOT NULL DEFAULT 0,
    flag          TEXT NOT NULL DEFAULT 'ranked'
                  CHECK (flag IN ('ranked', 'topic_uncertain')),
    reason        TEXT,                -- one line, shown in the UI
    UNIQUE (request_id, offering_id)
);

-- The gen-ed buckets this recommendation would close. This is the double count
-- (D-11, D-19, F-41) made explicit and auditable per result.
CREATE TABLE recommendation_bucket (
    recommendation_id INTEGER NOT NULL REFERENCES recommendation(recommendation_id),
    bucket_id         INTEGER NOT NULL REFERENCES gen_ed_bucket(bucket_id),
    PRIMARY KEY (recommendation_id, bucket_id)
);


-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX idx_offering_term      ON course_offering(term);
CREATE INDEX idx_offering_course    ON course_offering(course_id);
CREATE INDEX idx_offattr_bucket     ON offering_attribute(bucket_id);
CREATE INDEX idx_completed_student  ON completed_course(student_id);
CREATE INDEX idx_rec_request        ON recommendation(request_id);
CREATE INDEX idx_student_advisor    ON student(advisor_id);
